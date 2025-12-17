"""
services.py — Logique métier (use-cases)

Pourquoi ce fichier ?
- Centraliser la logique métier (et pas dans la CLI).
- Orchestrer validation + repository + calculs.
- Avoir des fonctions facilement testables.

Ce qui est déjà fait :
- Initialisation JSON → SQLite (reset DB)
- Listing inventaire

Ce que vous devez faire :
- Implémenter les autres use-cases : CRUD, vente, dashboard, export.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from .config import AppConfig
from .models import Product, now_iso
from .repository import SQLiteRepository
from .utils import load_initial_json

logger = logging.getLogger(__name__)


class InventoryManager:
    """Service principal du domaine 'stock'."""

    def __init__(self, config: AppConfig, repo: Optional[SQLiteRepository] = None) -> None:
        self.config = config
        self.repo = repo or SQLiteRepository(config.db_path)

    def initialize_from_json(self, json_path: str, reset: bool = True) -> int:
        """Initialise la DB depuis un JSON."""
        logger.info("Initialization requested from JSON: %s", json_path)
        payload = load_initial_json(json_path)
        products = payload["products"]

        if reset:
            self.repo.reset_and_create_schema()
        else:
            self.repo.create_schema_if_needed()

        count = 0
        for p in products:
            prod = Product(
                sku=p["sku"],
                name=p["name"],
                category=p["category"],
                unit_price_ht=p["unit_price_ht"],
                quantity=p["quantity"],
                vat_rate=p["vat_rate"],
                created_at=now_iso(),
            )
            self.repo.insert_product(prod)
            count += 1

        logger.info("Initialization OK. %d products inserted.", count)
        return count

    def list_inventory(self) -> List[Product]:
        """Retourne la liste des produits (inventaire)."""
        self.repo.create_schema_if_needed()
        return self.repo.list_products()

    def add_product(self, sku: str, name: str, category: str, unit_price_ht: float,
                    quantity: int, vat_rate: float = 0.20) -> int:
        """Ajoute un nouveau produit."""
        product = Product(
            sku=sku,
            name=name,
            category=category,
            unit_price_ht=unit_price_ht,
            quantity=quantity,
            vat_rate=vat_rate,
            created_at=now_iso(),
        )
        return self.repo.insert_product(product)

    def get_product(self, product_id: int) -> Optional[Product]:
        """Récupère un produit par son ID."""
        self.repo.create_schema_if_needed()
        return self.repo.get_product_by_id(product_id)

    def update_product(self, product_id: int,
                       name: Optional[str] = None,
                       category: Optional[str] = None,
                       unit_price_ht: Optional[float] = None,
                       quantity: Optional[int] = None,
                       vat_rate: Optional[float] = None) -> None:
        """Met à jour un produit existant (champs optionnels)."""
        existing = self.repo.get_product_by_id(product_id)
        if not existing:
            raise InventoryError(f"Produit ID={product_id} introuvable.")

        # On crée une nouvelle instance avec les champs modifiés
        # (Product est immuable/frozen, donc on remplace)
        updated = Product(
            id=existing.id,
            sku=existing.sku,  # Le SKU ne change généralement pas
            name=name if name is not None else existing.name,
            category=category if category is not None else existing.category,
            unit_price_ht=unit_price_ht if unit_price_ht is not None else existing.unit_price_ht,
            quantity=quantity if quantity is not None else existing.quantity,
            vat_rate=vat_rate if vat_rate is not None else existing.vat_rate,
            created_at=existing.created_at,
        )
        self.repo.update_product(updated)

    # TODO (étudiant) :
    # - delete_product
    # - sell_product (transaction atomique + calculs)
    # - dashboard (totaux)
    # - export_sales_csv
