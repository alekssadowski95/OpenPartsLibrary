import uuid
from decimal import Decimal, InvalidOperation
import re

from sqlalchemy.orm import selectinload

from openpartslibrary.models import BillOfMaterials, BillOfMaterialsItem, Component


BOM_NUMBER_PREFIX = "BOM"


def ensure_part_boms(session):
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
    try:
        quantity = Decimal(str(value or "1"))
    except (InvalidOperation, ValueError):
        quantity = Decimal("1")

    if quantity <= 0 or quantity != quantity.to_integral_value():
        return Decimal("1")
    return quantity.to_integral_value()


def next_bom_number(session):
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
    return format_cost_totals(bom_cost_totals(bom))


def bom_contains(session, root_bom_id, searched_bom_id):
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
            note=str(item.get("note") or "").strip() or None,
        ))

    session.commit()
    return bom


def get_created_boms(session):
    return (
        session.query(BillOfMaterials)
        .options(selectinload(BillOfMaterials.children).selectinload(BillOfMaterialsItem.child_bom))
        .filter(BillOfMaterials.is_part_wrapper.is_(False))
        .order_by(BillOfMaterials.date_modified.desc(), BillOfMaterials.name)
        .all()
    )


def get_bom_options(session):
    boms = (
        session.query(BillOfMaterials)
        .outerjoin(BillOfMaterials.component)
        .order_by(BillOfMaterials.is_part_wrapper, BillOfMaterials.name)
        .all()
    )
    return [
        {
            "id": bom.id,
            "name": bom.name,
            "number": bom.number or "",
            "is_part_wrapper": bom.is_part_wrapper,
            "label": f"{bom.number + ' - ' if bom.number else ''}{bom.name}",
            "display_label": f"{bom.number + ' - ' if bom.number else ''}{bom.name}",
        }
        for bom in boms
    ]
