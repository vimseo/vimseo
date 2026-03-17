# Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

"""
claude.ai (Sonnet 4.6), 19/02/2026.
Prompt: "Peux tu générer un maillage avec une taille de maille paramétrée à partir du fichier fournit ?
Génération de maillage 2D - Couette Flow paramétrique"
Fichier: https://github.com/PyFR/PyFR-Test-Cases/raw/main/2d-couette-flow/couette-flow.msh

Reproduit la structure du fichier couette-flow.msh fourni par PyFR-Test-Cases.

Géométrie :
  Domaine rectangulaire [-1, 1] x [0, 1]
  - Paroi inférieure (y=0) : bcwalllower  -> no-slip fixe
  - Paroi supérieure (y=1) : bcwallupper  -> no-slip mobile (vitesse imposée)
  - Gauche  (x=-1)         : periodic_0_l -> condition périodique
  - Droite  (x=+1)         : periodic_0_r -> condition périodique

Physical Groups (identiques au fichier original) :
  1D : periodic_0_r (tag 2), periodic_0_l (tag 3), bcwalllower (tag 4), bcwallupper (tag 5)
  2D : Fluid (tag 1)

Paramètre principal : mesh_size (taille de maille globale)
  - mesh_size = 0.25  -> ~55 noeuds  (résolution originale du fichier fourni)
  - mesh_size = 0.15  -> maillage intermédiaire
  - mesh_size = 0.08  -> maillage fin
  - mesh_size = 0.04  -> maillage très fin

Usage :
  python gmsh_couette_parametric.py
  python gmsh_couette_parametric.py --mesh_size 0.1
  python gmsh_couette_parametric.py --mesh_size 0.05 --output couette_fine.msh
  python gmsh_couette_parametric.py --sweep   # génère une série de maillages
"""

import argparse
import os

os.environ["DISPLAY"] = ""  # pas d'écran
import gmsh

gmsh.initialize(["-nopopup"])


def generate_couette_mesh(
    mesh_size: float = 0.25,
    lx: float = 2.0,  # largeur du domaine  (de -1 à +1)
    ly: float = 1.0,  # hauteur du domaine  (de  0 à  1)
    msh_version: float = 2.2,
    output: str = "couette_flow.msh",
    verbose: bool = True,
):
    """
    Génère un maillage 2D de Couette Flow.

    Schéma de la géométrie :

    y=1   2 ──────── bcwallupper ──────────── 4
          │                                   │
    per.  │         Domaine Fluid             │  per.
    0_l   │                                   │  0_r
          │                                   │
    y=0   1 ──────── bcwalllower ──────────── 3
        x=-1                               x=+1

    Paramètres
    ----------
    mesh_size          : taille de maille cible (paramètre principal)
    lx          : largeur totale du domaine (défaut 2.0, de x=-1 à x=+1)
    ly          : hauteur du domaine (défaut 1.0)
    msh_version : version du format .msh (2.2 recommandé pour PyFR)
    output      : nom du fichier de sortie
    verbose     : afficher les statistiques
    """

    x_left = -lx / 2  # x = -1
    x_right = lx / 2  # x = +1
    y_bot = 0.0
    y_top = ly  # y =  1

    gmsh.initialize()
    gmsh.model.add("couette_flow_2d")

    # ------------------------------------------------------------------
    # 1. POINTS (4 coins du rectangle)
    # ------------------------------------------------------------------
    p1 = gmsh.model.geo.addPoint(x_left, y_bot, 0, mesh_size)  # bas-gauche
    p2 = gmsh.model.geo.addPoint(x_left, y_top, 0, mesh_size)  # haut-gauche
    p3 = gmsh.model.geo.addPoint(x_right, y_bot, 0, mesh_size)  # bas-droite
    p4 = gmsh.model.geo.addPoint(x_right, y_top, 0, mesh_size)  # haut-droite

    # ------------------------------------------------------------------
    # 2. LIGNES
    # ------------------------------------------------------------------
    l_left = gmsh.model.geo.addLine(p1, p2)  # x=-1 : periodic_0_l
    l_right = gmsh.model.geo.addLine(p3, p4)  # x=+1 : periodic_0_r
    l_bot = gmsh.model.geo.addLine(p1, p3)  # y=0  : bcwalllower
    l_top = gmsh.model.geo.addLine(p2, p4)  # y=1  : bcwallupper

    # ------------------------------------------------------------------
    # 3. SURFACE (sens anti-horaire)
    # ------------------------------------------------------------------
    cl = gmsh.model.geo.addCurveLoop([l_bot, l_right, -l_top, -l_left])
    surf = gmsh.model.geo.addPlaneSurface([cl])

    gmsh.model.geo.synchronize()

    # ------------------------------------------------------------------
    # 4. PÉRIODICITÉ (gauche <-> droite)
    # Translation en x de -lx (de droite vers gauche)
    # ------------------------------------------------------------------
    # Matrice de transformation 4x4 (translation) : [1,0,0,dx, 0,1,0,0, 0,0,1,0, 0,0,0,1]
    translation = [1, 0, 0, -lx, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    gmsh.model.mesh.setPeriodic(1, [l_left], [l_right], translation)

    # ------------------------------------------------------------------
    # 5. PHYSICAL GROUPS
    # Tags identiques au fichier original pour compatibilité PyFR
    # ------------------------------------------------------------------
    gmsh.model.addPhysicalGroup(1, [l_right], tag=2, name="periodic_0_r")
    gmsh.model.addPhysicalGroup(1, [l_left], tag=3, name="periodic_0_l")
    gmsh.model.addPhysicalGroup(1, [l_bot], tag=4, name="bcwalllower")
    gmsh.model.addPhysicalGroup(1, [l_top], tag=5, name="bcwallupper")
    gmsh.model.addPhysicalGroup(2, [surf], tag=1, name="Fluid")

    # ------------------------------------------------------------------
    # 6. OPTIONS DE MAILLAGE
    # ------------------------------------------------------------------
    gmsh.option.setNumber("Mesh.Algorithm", 6)  # Frontal-Delaunay 2D
    gmsh.option.setNumber("Mesh.Smoothing", 5)  # lissage Laplacien
    gmsh.option.setNumber("Mesh.RecombineAll", 0)  # triangles (comme l'original)
    gmsh.option.setNumber("Mesh.MshFileVersion", msh_version)
    gmsh.option.setNumber("Mesh.Binary", 0)  # ASCII

    # ------------------------------------------------------------------
    # 7. GÉNÉRATION ET EXPORT
    # ------------------------------------------------------------------
    gmsh.model.mesh.generate(2)
    gmsh.model.mesh.optimize("Netgen")

    gmsh.write(output)

    if verbose:
        nodes = gmsh.model.mesh.getNodes()[0].shape[0]
        _, elem_tags, _ = gmsh.model.mesh.getElements(2)
        n_elems = sum(len(t) for t in elem_tags)
        print(f"[OK] {output}")
        print(f"     mesh_size = {mesh_size}")
        print(f"     Nœuds    : {nodes}")
        print(f"     Éléments : {n_elems}")
        print(f"     Format   : MSH {msh_version}")

    gmsh.finalize()
    return output


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description="Maillage 2D Couette Flow paramétrique pour PyFR."
    )
    parser.add_argument(
        "--mesh_size",
        type=float,
        default=0.25,
        help="Taille de maille globale (défaut: 0.25, identique à l'original)",
    )
    parser.add_argument(
        "--lx",
        type=float,
        default=2.0,
        help="Largeur du domaine (défaut: 2.0, de x=-1 à x=+1)",
    )
    parser.add_argument(
        "--ly", type=float, default=1.0, help="Hauteur du domaine (défaut: 1.0)"
    )
    parser.add_argument(
        "--msh",
        type=float,
        default=2.2,
        help="Version du format .msh (2.2 ou 4.1, défaut: 2.2)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Nom du fichier de sortie (défaut: couette_lc<valeur>.msh)",
    )
    parser.add_argument(
        "--sweep",
        action="store_true",
        help="Générer une série de maillages pour étude de convergence",
    )
    return parser.parse_args()
