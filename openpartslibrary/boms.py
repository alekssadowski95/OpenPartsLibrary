"""Business logic for persistent and generated bills of materials."""

import uuid
from decimal import Decimal, InvalidOperation
import re

from sqlalchemy.orm import selectinload

from openpartslibrary.models import BillOfMaterials, BillOfMaterialsItem, Component


BOM_NUMBER_PREFIX = "BOM"


def ensure_part_boms(session):
    """Create or update one part-wrapper BOM for every component.

    :param session: SQLAlchemy session.
    :return: ``None``.
    """

    components = session.query(Component).all()
    existing_by_component_id = {
        bom.component_id: bom
        for bom in session.query(BillOfMaterials)
        .filter(BillOfMaterials.component_id.isnot(None))
        .all()
    }

    changed = False
    for component in components:
        bom = existing_by_component_id.get(component.id)
        if bom is None:
            bom = BillOfMaterials(
                uuid=str(uuid.uuid4()),
                number=component.number,
                name=component.name,
                description=component.description,
                component=component,
                is_part_wrapper=True,
            )
            session.add(bom)
            changed = True
            continue

        if bom.name != component.name or bom.number != component.number or bom.description != component.description:
            bom.name = component.name
            bom.number = component.number
            bom.description = component.description
            bom.is_part_wrapper = True
            changed = True

    if changed:
        session.commit()


def decimal_quantity(value):
    """Normalize user-entered quantities to positive whole-number decimals.

    :param value: Raw quantity from a form, JSON payload, or database value.
    :return: Valid positive integer quantity as :class:`decimal.Decimal`.
    """

    try:
        quantity = Decimal(str(value or "1"))
    except (InvalidOperation, ValueError):
        quantity = Decimal("1")

    if quantity <= 0 or quantity != quantity.to_integral_value():
        return Decimal("1")
    return quantity.to_integral_value()


def next_bom_number(session):
    """Return the next generated BOM number.

    :param session: SQLAlchemy session.
    :return: Number in the ``BOM000001`` style.
    :rtype: str
    """

    highest_number = 0
    existing_numbers = (
        session.query(BillOfMaterials.number)
        .filter(
            BillOfMaterials.is_part_wrapper.is_(False),
            BillOfMaterials.number.isnot(None),
        )
        .all()
    )
    for row in existing_numbers:
        number = row[0] or ""
        match = re.fullmatch(rf"{BOM_NUMBER_PREFIX}(\d+)", number.strip())
        if match:
            highest_number = max(highest_number, int(match.group(1)))

    return f"{BOM_NUMBER_PREFIX}{highest_number + 1:06d}"


def bom_cost_totals(bom, visited=None):
    """Calculate recursive BOM cost totals grouped by currency.

    :param bom: BOM-like object with ``children`` and ``is_part_wrapper``.
    :param visited: Internal cycle-protection set.
    :return: Mapping of currency code to total amount.
    :rtype: dict[str, decimal.Decimal]
    """

    visited = set(visited or set())
    if bom is None or bom.id in visited:
        return {}

    next_visited = visited | {bom.id}
    if bom.is_part_wrapper:
        component = bom.component
        if component is None or component.unit_price is None:
            return {}
        try:
            unit_price = Decimal(str(component.unit_price))
        except (InvalidOperation, ValueError):
            return {}
        if unit_price <= 0:
            return {}
        return {component.currency or "": unit_price}

    totals = {}
    for item in sorted(bom.children, key=lambda child: (child.position, child.id)):
        quantity = decimal_quantity(item.quantity)
        for currency, amount in bom_cost_totals(item.child_bom, next_visited).items():
            totals[currency] = totals.get(currency, Decimal("0")) + (amount * quantity)
    return totals


def format_cost_totals(totals):
    """Format currency totals for display.

    :param totals: Mapping returned by :func:`bom_cost_totals`.
    :return: Human-readable cost string or ``-``.
    :rtype: str
    """

    visible_totals = [
        (currency, amount)
        for currency, amount in sorted(totals.items(), key=lambda row: row[0])
        if amount > 0
    ]
    if not visible_totals:
        return "-"
    return " + ".join(
        f"{amount.quantize(Decimal('0.01'))} {currency}".strip()
        for currency, amount in visible_totals
    )


def format_bom_cost(bom):
    """Format a BOM's recursive total cost for templates."""

    return format_cost_totals(bom_cost_totals(bom))


def bom_contains(session, root_bom_id, searched_bom_id):
    """Check whether one BOM exists inside another BOM tree.

    :return: ``True`` when ``searched_bom_id`` is in the root tree.
    :rtype: bool
    """

    if root_bom_id == searched_bom_id:
        return True

    visited = set()
    stack = [root_bom_id]
    while stack:
        bom_id = stack.pop()
        if bom_id in visited:
            continue
        visited.add(bom_id)

        child_ids = [
            row[0]
            for row in session.query(BillOfMaterialsItem.child_bom_id)
            .filter(BillOfMaterialsItem.parent_bom_id == bom_id)
            .all()
        ]
        if searched_bom_id in child_ids:
            return True
        stack.extend(child_ids)

    return False


def create_bom(session, name, description="", items=None, number=None):
    """Create a persistent BOM and attach validated child items.

    :param session: SQLAlchemy session.
    :param name: BOM display name.
    :param description: Optional BOM description.
    :param items: Child BOM dictionaries containing IDs and quantities.
    :param number: Optional explicit BOM number.
    :return: Created BOM model.
    """

    bom = BillOfMaterials(
        uuid=str(uuid.uuid4()),
        name=str(name or "").strip(),
        number=str(number or "").strip() or next_bom_number(session),
        description=str(description or "").strip() or None,
        is_part_wrapper=False,
    )
    session.add(bom)
    session.flush()

    for position, item in enumerate(items or [], start=1):
        child_bom_id = item.get("child_bom_id")
        if not child_bom_id:
            continue
        child_bom = session.query(BillOfMaterials).filter_by(id=int(child_bom_id)).first()
        if child_bom is None or bom_contains(session, child_bom.id, bom.id):
            continue

        session.add(BillOfMaterialsItem(
            parent_bom=bom,
            child_bom=child_bom,
            quantity=decimal_quantity(item.get("quantity")),
            position=position,
        ))

    session.commit()
    return bom


def replace_bom_items(session, bom, items=None):
    """Replace a BOM's children with validated child item rows.

    :param session: SQLAlchemy session.
    :param bom: BOM model to update.
    :param items: Child BOM dictionaries containing IDs and quantities.
    :return: ``None``.
    """

    for item in list(bom.children):
        session.delete(item)
    session.flush()

    for position, item in enumerate(items or [], start=1):
        child_bom_id = item.get("child_bom_id")
        if not child_bom_id:
            continue
        child_bom = session.query(BillOfMaterials).filter_by(id=int(child_bom_id)).first()
        if child_bom is None or child_bom.id == bom.id or bom_contains(session, child_bom.id, bom.id):
            continue
        session.add(BillOfMaterialsItem(
            parent_bom=bom,
            child_bom=child_bom,
            quantity=decimal_quantity(item.get("quantity")),
            position=position,
        ))


def update_bom(session, bom, name, description="", items=None):
    """Update a BOM's metadata and child items."""

    bom.name = str(name or "").strip()
    bom.description = str(description or "").strip() or None
    replace_bom_items(session, bom, items)
    session.commit()
    return bom


def copy_bom(session, bom):
    """Create a shallow copy of a BOM and its child item references."""

    copied_bom = BillOfMaterials(
        uuid=str(uuid.uuid4()),
        name=f"{bom.name} (copy)",
        number=next_bom_number(session),
        description=bom.description,
        is_part_wrapper=False,
    )
    session.add(copied_bom)
    session.flush()
    replace_bom_items(
        session,
        copied_bom,
        [
            {
                "child_bom_id": item.child_bom_id,
                "quantity": item.quantity,
            }
            for item in sorted(bom.children, key=lambda child: (child.position, child.id))
        ],
    )
    session.commit()
    return copied_bom


def bom_part_quantities(bom, multiplier=Decimal("1"), visited=None):
    """Flatten a BOM tree into total part quantities.

    :param bom: BOM-like object.
    :param multiplier: Quantity multiplier passed during recursion.
    :param visited: Internal cycle-protection set.
    :return: Mapping of component UUID to component/quantity rows.
    :rtype: dict
    """

    visited = set(visited or set())
    if bom is None or bom.id in visited:
        return {}

    next_visited = visited | {bom.id}
    if bom.is_part_wrapper:
        return {bom.component.uuid: {"component": bom.component, "quantity": int(multiplier)}} if bom.component else {}

    parts = {}
    for item in sorted(bom.children, key=lambda child: (child.position, child.id)):
        item_quantity = multiplier * decimal_quantity(item.quantity)
        for component_uuid, row in bom_part_quantities(item.child_bom, item_quantity, next_visited).items():
            if component_uuid not in parts:
                parts[component_uuid] = {"component": row["component"], "quantity": 0}
            parts[component_uuid]["quantity"] += row["quantity"]
    return parts


def get_created_boms(session):
    """Return user-created persistent BOMs sorted for display."""

    return (
        session.query(BillOfMaterials)
        .options(selectinload(BillOfMaterials.children).selectinload(BillOfMaterialsItem.child_bom))
        .filter(BillOfMaterials.is_part_wrapper.is_(False))
        .order_by(BillOfMaterials.date_modified.desc(), BillOfMaterials.name)
        .all()
    )


def get_bom_options(session):
    """Return JSON-serializable BOM picker options for editors."""

    boms = (
        session.query(BillOfMaterials)
        .options(selectinload(BillOfMaterials.children).selectinload(BillOfMaterialsItem.child_bom))
        .outerjoin(BillOfMaterials.component)
        .order_by(BillOfMaterials.is_part_wrapper, BillOfMaterials.name)
        .all()
    )
    labels_by_id = {
        bom.id: f"{bom.number + ' - ' if bom.number else ''}{bom.name}"
        for bom in boms
    }
    boms_by_id = {bom.id: bom for bom in boms}

    def cost_totals_for_option(bom):
        return {
            currency: str(amount)
            for currency, amount in bom_cost_totals(bom).items()
        }

    def readonly_children_for_bom(bom, visited=None):
        visited = set(visited or set())
        if bom is None or bom.is_part_wrapper or bom.id in visited:
            return []

        next_visited = visited | {bom.id}
        children = []
        for item in sorted(bom.children, key=lambda child: (child.position, child.id)):
            child_bom = item.child_bom
            children.append({
                "child_bom_id": item.child_bom_id,
                "display_label": labels_by_id.get(item.child_bom_id, ""),
                "source_type": "existing",
                "readonly": True,
                "new_bom_name": "",
                "new_bom_description": "",
                "quantity": str(item.quantity.normalize() if item.quantity else 1),
                "children": readonly_children_for_bom(child_bom, next_visited),
            })
        return children

    return [
        {
            "id": bom.id,
            "name": bom.name,
            "number": bom.number or "",
            "is_part_wrapper": bom.is_part_wrapper,
            "label": f"{bom.number + ' - ' if bom.number else ''}{bom.name}",
            "display_label": f"{bom.number + ' - ' if bom.number else ''}{bom.name}",
            "cost_totals": cost_totals_for_option(bom),
            "children": readonly_children_for_bom(boms_by_id.get(bom.id)),
        }
        for bom in boms
    ]
