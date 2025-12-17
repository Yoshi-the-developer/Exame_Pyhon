"""
cli.py — Interface console (menu interactif)

Pourquoi ce fichier ?
- C’est la couche “présentation” : inputs utilisateur, affichage, navigation menu.
- Elle doit rester simple : pas de SQL direct ici, pas de calcul métier complexe ici.

Ce qui est déjà fait (starter) :
- Menu interactif complet (8 options)
- Option 1 : Initialisation JSON → SQLite (fonctionnelle)
- Option 2 : Afficher inventaire (fonctionnelle)
- Les options 3 à 7 sont des TODO guidés

Ce que vous devez faire :
- Implémenter progressivement les options 3..7 en appelant `InventoryManager`.
"""

from __future__ import annotations

import argparse
import logging

from .config import AppConfig
from .exceptions import (
    DataImportError,
    DatabaseError,
    InventoryError,
    ValidationError,
)
from .logging_conf import configure_logging
from .services import InventoryManager
from .utils import format_table

logger = logging.getLogger(__name__)


def _prompt(text: str) -> str:
    return input(text).strip()


def print_menu() -> None:
    print("\n=== Gestion de stock (JSON → SQLite) ===")
    print("1) Initialiser le stock (depuis un JSON)")
    print("2) Afficher l’inventaire")
    print("3) Ajouter un produit")
    print("4) Modifier un produit")
    print("5) Supprimer un produit (TODO)")
    print("6) Vendre un produit    (TODO)")
    print("7) Tableau de bord      (TODO)")
    print("8) Quitter")


def render_inventory_table(products) -> str:
    headers = ["ID", "SKU", "Nom", "Catégorie", "Prix HT", "TVA", "Prix TTC", "Stock"]
    rows = []
    for p in products:
        unit_ttc = round(p.unit_price_ht * (1 + p.vat_rate), 2)
        rows.append([
            str(p.id or ""),
            p.sku,
            p.name,
            p.category,
            f"{p.unit_price_ht:.2f}",
            f"{p.vat_rate:.2f}",
            f"{unit_ttc:.2f}",
            str(p.quantity),
        ])
    return format_table(headers, rows)


def action_initialize(app: InventoryManager) -> None:
    default_path = "data/initial_stock.json"
    path = _prompt(f"Chemin du JSON d'initialisation [{default_path}] : ")
    path = path or default_path
    count = app.initialize_from_json(path, reset=True)
    print(f"Initialisation réussie : {count} produit(s) importé(s).")


def action_list_inventory(app: InventoryManager) -> None:
    products = app.list_inventory()
    if not products:
        print("(inventaire vide)")
        return
    print("\n" + render_inventory_table(products))


def action_add_product(app: InventoryManager) -> None:
    print("\n[Ajout de produit]")
    sku = _prompt("SKU (unique) : ")
    if not sku:
        print("Erreur : Le SKU ne peut pas être vide.")
        return

    name = _prompt("Nom : ")
    category = _prompt("Catégorie : ")

    try:
        price_str = _prompt("Prix HT : ")
        unit_price_ht = float(price_str)
        if unit_price_ht < 0:
            raise ValueError("Le prix doit être positif.")

        qty_str = _prompt("Quantité initiale : ")
        quantity = int(qty_str)
        if quantity < 0:
            raise ValueError("La quantité doit être positive.")

        vat_str = _prompt("Taux de TVA (0.20 par défaut) : ")
        vat_rate = float(vat_str) if vat_str else 0.20
        if not (0 <= vat_rate <= 1):
            raise ValueError("Le taux de TVA doit être entre 0 et 1.")

    except ValueError as e:
        print(f"Erreur de saisie : {e}")
        return

    try:
        new_id = app.add_product(
            sku=sku,
            name=name,
            category=category,
            unit_price_ht=unit_price_ht,
            quantity=quantity,
            vat_rate=vat_rate,
        )
        print(f"Succès ! Produit ajouté avec l'ID {new_id}.")
    except Exception as e:
        print(f"Erreur lors de l'ajout : {e}")



def action_update_product(app: InventoryManager) -> None:
    print("\n[Modification de produit]")
    id_str = _prompt("ID du produit à modifier : ")
    if not id_str.isdigit():
        print("Erreur : L'ID doit être un nombre entier.")
        return
    
    product_id = int(id_str)
    product = app.get_product(product_id)
    if not product:
        print(f"Erreur : Aucun produit trouvé avec l'ID {product_id}.")
        return

    print(f"Modification de : {product.name} (SKU: {product.sku})")
    print("Laissez vide pour conserver la valeur actuelle.")

    name = _prompt(f"Nouveau nom [{product.name}] : ")
    category = _prompt(f"Nouvelle catégorie [{product.category}] : ")
    
    price_ht = None
    price_str = _prompt(f"Nouveau prix HT [{product.unit_price_ht}] : ")
    if price_str:
        try:
            val = float(price_str)
            if val < 0:
                print("Erreur : prix négatif.")
                return
            price_ht = val
        except ValueError:
            print("Erreur : format de prix invalide.")
            return

    quantity = None
    qty_str = _prompt(f"Nouvelle quantité [{product.quantity}] : ")
    if qty_str:
        try:
            val = int(qty_str)
            if val < 0:
                print("Erreur : quantité négative.")
                return
            quantity = val
        except ValueError:
            print("Erreur : format de quantité invalide.")
            return

    vat_rate = None
    vat_str = _prompt(f"Nouveau taux TVA [{product.vat_rate}] : ")
    if vat_str:
        try:
            val = float(vat_str)
            if not (0 <= val <= 1):
                print("Erreur : TVA hors limites (0-1).")
                return
            vat_rate = val
        except ValueError:
            print("Erreur : format de TVA invalide.")
            return

    try:
        app.update_product(
            product_id=product_id,
            name=name if name else None,
            category=category if category else None,
            unit_price_ht=price_ht,
            quantity=quantity,
            vat_rate=vat_rate,
        )
        print("Succès ! Produit mis à jour.")
    except Exception as e:
        print(f"Erreur lors de la mise à jour : {e}")

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Inventory CLI — starter kit")
    p.add_argument("--db", default="data/inventory.db", help="Chemin du fichier SQLite (.db)")
    p.add_argument("--log-level", default="INFO", help="DEBUG/INFO/WARNING/ERROR")
    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    configure_logging(log_level=args.log_level)
    config = AppConfig(db_path=args.db)
    app = InventoryManager(config)

    logger.info("App started with db=%s", config.db_path)

    while True:
        try:
            print_menu()
            choice = _prompt("Votre choix (1-8) : ")

            if choice == "1":
                action_initialize(app)
            elif choice == "2":
                action_list_inventory(app)
            elif choice == "3":
                action_add_product(app)
            elif choice == "4":
                action_update_product(app)
            elif choice in {"5", "6", "7"}:
                print("Fonctionnalité TODO : à implémenter par l'étudiant selon l'énoncé.")
            elif choice == "8":
                print("Au revoir.")
                return 0
            else:
                print("Choix invalide. Veuillez saisir un nombre entre 1 et 8.")

        except (ValidationError, DataImportError) as e:
            logger.warning("Validation/import error: %s", e)
            print(f"Erreur: {e}")
        except DatabaseError as e:
            logger.error("Database error: %s", e)
            print(f"Erreur base de données: {e}")
        except InventoryError as e:
            logger.error("Inventory error: %s", e)
            print(f"Erreur: {e}")
        except KeyboardInterrupt:
            print("\nInterruption utilisateur. Au revoir.")
            return 130
        except Exception:
            logger.exception("Unexpected error")
            print("Erreur inattendue. Consultez le fichier de logs.")
            return 1
