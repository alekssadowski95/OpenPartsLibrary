import math
from collections import defaultdict
from datetime import datetime, timedelta

try:
    from flask_admin import Admin, AdminIndexView, expose
    from flask_admin.contrib.sqla import ModelView
except ImportError:
    Admin = None
    AdminIndexView = None
    expose = None
    ModelView = None

from flask import redirect, render_template_string, request, url_for
from markupsafe import escape

from openpartslibrary.boms import copy_bom, create_bom, ensure_part_boms, format_bom_cost, get_bom_options, get_created_boms, update_bom
from openpartslibrary.i18n import gettext as _, lazy_gettext
from openpartslibrary.models import BillOfMaterials, BillOfMaterialsItem, Component, ComponentComponent, DownloadEvent, File, Material, Supplier


DOWNLOAD_DASHBOARD_TIMEFRAMES = {
    "7d": ("Last 7 days", 7),
    "30d": ("Last 30 days", 30),
    "90d": ("Last 90 days", 90),
    "365d": ("Last 12 months", 365),
    "all": ("All time", None),
}


def download_event_quantity(event):
    return 1


def download_part_key(event):
    if not event.component_uuid:
        return None
    return (
        event.component_uuid,
        event.component_number or "",
        event.component_name or _("Unknown part"),
    )


def get_download_dashboard_data(session, timeframe_key):
    timeframe_key = timeframe_key if timeframe_key in DOWNLOAD_DASHBOARD_TIMEFRAMES else "30d"
    timeframe_label, timeframe_days = DOWNLOAD_DASHBOARD_TIMEFRAMES[timeframe_key]
    now = datetime.utcnow()
    start_date = now - timedelta(days=timeframe_days) if timeframe_days else None

    query = session.query(DownloadEvent)
    if start_date is not None:
        query = query.filter(DownloadEvent.date_downloaded >= start_date)
    events = query.order_by(DownloadEvent.date_downloaded.asc()).all()

    chart_counts = defaultdict(int)
    part_counts = defaultdict(lambda: {"part_number": "", "part_name": "", "count": 0})
    recent_counts = defaultdict(lambda: {"part_number": "", "part_name": "", "count": 0})
    previous_counts = defaultdict(lambda: {"part_number": "", "part_name": "", "count": 0})

    if timeframe_days:
        recent_window_days = max(1, min(14, timeframe_days // 2))
    else:
        recent_window_days = 30
    recent_start = now - timedelta(days=recent_window_days)
    previous_start = recent_start - timedelta(days=recent_window_days)

    for event in events:
        quantity = download_event_quantity(event)
        chart_counts[event.date_downloaded.date().isoformat()] += quantity

        part_key = download_part_key(event)
        if part_key is None:
            continue

        component_uuid, part_number, part_name = part_key
        part_counts[component_uuid]["part_number"] = part_number
        part_counts[component_uuid]["part_name"] = part_name
        part_counts[component_uuid]["count"] += quantity

        if event.date_downloaded >= recent_start:
            recent_counts[component_uuid]["part_number"] = part_number
            recent_counts[component_uuid]["part_name"] = part_name
            recent_counts[component_uuid]["count"] += quantity
        elif event.date_downloaded >= previous_start:
            previous_counts[component_uuid]["part_number"] = part_number
            previous_counts[component_uuid]["part_name"] = part_name
            previous_counts[component_uuid]["count"] += quantity

    if timeframe_days:
        chart_start = start_date.date()
        chart_labels = [
            (chart_start + timedelta(days=day_offset)).isoformat()
            for day_offset in range(timeframe_days + 1)
        ]
    else:
        chart_labels = sorted(chart_counts)

    chart_values = [chart_counts[label] for label in chart_labels]

    most_downloaded = sorted(
        part_counts.values(),
        key=lambda row: (-row["count"], row["part_name"].lower()),
    )[:10]

    trending_rows = []
    for component_uuid, recent_row in recent_counts.items():
        recent_count = recent_row["count"]
        previous_count = previous_counts[component_uuid]["count"]
        absolute_increase = recent_count - previous_count
        if recent_count <= 0 or absolute_increase <= 0:
            continue

        percent_increase = (absolute_increase / max(previous_count, 1)) * 100
        trend_score = absolute_increase * math.log1p(recent_count) + percent_increase
        trending_rows.append({
            "part_number": recent_row["part_number"],
            "part_name": recent_row["part_name"],
            "recent_count": recent_count,
            "previous_count": previous_count,
            "absolute_increase": absolute_increase,
            "percent_increase": percent_increase,
            "trend_score": trend_score,
        })

    trending_rows.sort(key=lambda row: (-row["trend_score"], -row["absolute_increase"], row["part_name"].lower()))

    return {
        "timeframe_key": timeframe_key,
        "timeframe_label": timeframe_label,
        "timeframes": DOWNLOAD_DASHBOARD_TIMEFRAMES,
        "translated_timeframes": {
            key: (_(label), days)
            for key, (label, days) in DOWNLOAD_DASHBOARD_TIMEFRAMES.items()
        },
        "total_downloads": sum(chart_values),
        "total_part_downloads": sum(row["count"] for row in part_counts.values()),
        "chart_labels": chart_labels,
        "chart_values": chart_values,
        "most_downloaded": most_downloaded,
        "trending": trending_rows[:10],
        "recent_window_days": recent_window_days,
    }


DOWNLOAD_DASHBOARD_TEMPLATE = """
{% import 'admin/layout.html' as layout with context %}
<!doctype html>
<html lang="{{ current_locale.replace('_', '-') }}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ _('Downloads Dashboard') }} | {{ _('OpenPartsLibrary Admin') }}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='bootstrap-5.3.3-dist/css/bootstrap.min.css') }}">
    <style>
        body { background: #f8f9fa; }
        .dashboard-card { background: white; border: 1px solid #dee2e6; border-radius: 6px; }
        .chart-wrap { height: 300px; position: relative; }
        .chart-tooltip {
            position: absolute;
            display: none;
            padding: 6px 8px;
            border-radius: 4px;
            background: rgba(4, 44, 97, 0.94);
            color: white;
            font-size: 0.8rem;
            pointer-events: none;
            transform: translate(-50%, -110%);
            white-space: nowrap;
            z-index: 5;
        }
        .metric { color: #6c757d; font-size: 0.85rem; }
        .opl-admin-header { width: 100%; background: #042c61; color: white; border-bottom: 1px solid #0a3b7a; }
        .opl-admin-header-inner { width: 100%; min-height: 52px; padding: 0 14px; display: flex; align-items: center; justify-content: space-between; gap: 16px; }
        .opl-admin-brand, .opl-admin-brand:hover { display: inline-flex; align-items: center; gap: 8px; color: white; text-decoration: none; font-size: 18px; white-space: nowrap; }
        .opl-admin-brand img { filter: brightness(0.5); }
        .opl-admin-header-right { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; justify-content: flex-end; }
        .opl-admin-navigation { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
        .opl-admin-nav-link, .opl-admin-nav-link:hover { display: inline-flex; align-items: center; min-height: 32px; padding: 4px 8px; border: 0; border-radius: 4px; background: transparent; color: white; text-decoration: none; font-size: 0.9rem; }
        .opl-admin-nav-link:hover { background: rgba(255, 255, 255, 0.14); }
        .opl-admin-navigation .dropdown-menu { margin-top: 8px; z-index: 1000; }
        .opl-admin-navigation .dropdown:hover .dropdown-menu, .opl-admin-navigation .dropdown:focus-within .dropdown-menu { display: block; }
        .opl-admin-header-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; justify-content: flex-end; }
        .opl-admin-header-actions a, .opl-admin-header-actions a:hover { color: white; text-decoration: none; font-size: 0.9rem; }
    </style>
</head>
<body>
    {% include 'admin/_header.html' %}
    <main class="container-fluid py-4">
        <div class="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3">
            <div>
                <h1 class="h3 mb-1">{{ _('Downloads Dashboard') }}</h1>
                <div class="metric">{{ _(data.timeframe_label) }} · {{ ngettext('%(num)s total download', '%(num)s total downloads', data.total_downloads) }}</div>
            </div>
            <div class="d-flex flex-wrap gap-2">
                {% for key, timeframe in data.translated_timeframes.items() %}
                <a class="btn btn-sm {{ 'btn-primary' if key == data.timeframe_key else 'btn-outline-secondary' }}" href="{{ dashboard_url }}?timeframe={{ key }}">{{ timeframe[0] }}</a>
                {% endfor %}
                <a class="btn btn-sm btn-outline-secondary" href="{{ admin_home_url }}">{{ _('Admin home') }}</a>
            </div>
        </div>

        <section class="dashboard-card p-3 mb-3">
            <div class="d-flex align-items-center justify-content-between mb-2">
                <h2 class="h5 mb-0">{{ _('Downloads over time') }}</h2>
                <span class="metric">{{ _('Daily totals') }}</span>
            </div>
            <div class="chart-wrap">
                <canvas id="downloads-chart" width="1200" height="300"></canvas>
                <div id="downloads-chart-tooltip" class="chart-tooltip"></div>
            </div>
        </section>

        <div class="row g-3">
            <section class="col-12 col-lg-6">
                <div class="dashboard-card p-3 h-100">
                    <h2 class="h5 mb-1">{{ _('Most downloaded parts') }}</h2>
                    <p class="metric mb-3">{{ _('Top parts in descending order by download count.') }}</p>
                    <div class="table-responsive">
                        <table class="table table-sm align-middle">
                            <thead>
                                <tr>
                                    <th>{{ _('Part number') }}</th>
                                    <th>{{ _('Name') }}</th>
                                    <th class="text-end">{{ _('Downloads') }}</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for row in data.most_downloaded %}
                                <tr>
                                    <td>{{ row.part_number }}</td>
                                    <td>{{ row.part_name }}</td>
                                    <td class="text-end">{{ row.count }}</td>
                                </tr>
                                {% else %}
                                <tr><td colspan="3" class="text-muted">{{ _('No part downloads in this timeframe.') }}</td></tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </section>
            <section class="col-12 col-lg-6">
                <div class="dashboard-card p-3 h-100">
                    <h2 class="h5 mb-1">{{ _('Trending downloads') }}</h2>
                    <p class="metric mb-3">{{ _('Ranks recent growth against the previous %(days)s days using absolute and percentage increase.', days=data.recent_window_days) }}</p>
                    <div class="table-responsive">
                        <table class="table table-sm align-middle">
                            <thead>
                                <tr>
                                    <th>{{ _('Part') }}</th>
                                    <th class="text-end">{{ _('Recent') }}</th>
                                    <th class="text-end">{{ _('Previous') }}</th>
                                    <th class="text-end">{{ _('Increase') }}</th>
                                    <th class="text-end">%</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for row in data.trending %}
                                <tr>
                                    <td>
                                        <div class="fw-semibold">{{ row.part_name }}</div>
                                        <div class="metric">{{ row.part_number }}</div>
                                    </td>
                                    <td class="text-end">{{ row.recent_count }}</td>
                                    <td class="text-end">{{ row.previous_count }}</td>
                                    <td class="text-end">+{{ row.absolute_increase }}</td>
                                    <td class="text-end">+{{ "%.0f"|format(row.percent_increase) }}%</td>
                                </tr>
                                {% else %}
                                <tr><td colspan="5" class="text-muted">{{ _('No trending downloads in this timeframe yet.') }}</td></tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </section>
        </div>
    </main>
    <script>
        const labels = {{ data.chart_labels|tojson }};
        const values = {{ data.chart_values|tojson }};
        const canvas = document.getElementById("downloads-chart");
        const tooltip = document.getElementById("downloads-chart-tooltip");
        const ctx = canvas.getContext("2d");
        const width = canvas.width;
        const height = canvas.height;
        const padding = 32;
        const maxValue = Math.max(...values, 1);

        ctx.clearRect(0, 0, width, height);
        ctx.strokeStyle = "#dee2e6";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(padding, padding);
        ctx.lineTo(padding, height - padding);
        ctx.lineTo(width - padding, height - padding);
        ctx.stroke();

        const usableWidth = width - (padding * 2);
        const usableHeight = height - (padding * 2);
        const step = values.length > 1 ? usableWidth / (values.length - 1) : usableWidth;
        const points = values.map((value, index) => ({
            label: labels[index],
            value,
            x: padding + (index * step),
            y: height - padding - ((value / maxValue) * usableHeight)
        }));

        ctx.strokeStyle = "#0d6efd";
        ctx.lineWidth = 3;
        ctx.beginPath();
        points.forEach((point, index) => {
            if (index === 0) {
                ctx.moveTo(point.x, point.y);
            } else {
                ctx.lineTo(point.x, point.y);
            }
        });
        ctx.stroke();

        ctx.fillStyle = "#0d6efd";
        points.forEach((point) => {
            ctx.beginPath();
            ctx.arc(point.x, point.y, 3, 0, Math.PI * 2);
            ctx.fill();
        });

        ctx.fillStyle = "#6c757d";
        ctx.font = "12px system-ui, sans-serif";
        ctx.fillText("0", 8, height - padding + 4);
        ctx.fillText(String(maxValue), 8, padding + 4);
        if (labels.length) {
            ctx.fillText(labels[0], padding, height - 8);
            const endLabel = labels[labels.length - 1];
            ctx.fillText(endLabel, width - padding - ctx.measureText(endLabel).width, height - 8);
        }

        canvas.addEventListener("mousemove", (event) => {
            if (!points.length) {
                return;
            }

            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            const mouseX = (event.clientX - rect.left) * scaleX;
            const mouseY = (event.clientY - rect.top) * scaleY;
            const nearest = points.reduce((closest, point) => {
                const distance = Math.hypot(point.x - mouseX, point.y - mouseY);
                return distance < closest.distance ? { point, distance } : closest;
            }, { point: null, distance: Number.POSITIVE_INFINITY });

            if (!nearest.point || nearest.distance > 18) {
                tooltip.style.display = "none";
                return;
            }

            const downloadLabel = nearest.point.value === 1 ? {{ _('download')|tojson }} : {{ _('downloads')|tojson }};
            tooltip.textContent = `${nearest.point.label}: ${nearest.point.value} ${downloadLabel}`;
            tooltip.style.left = `${nearest.point.x / scaleX}px`;
            tooltip.style.top = `${nearest.point.y / scaleY}px`;
            tooltip.style.display = "block";
        });

        canvas.addEventListener("mouseleave", () => {
            tooltip.style.display = "none";
        });
    </script>
</body>
</html>
"""


BOM_BUILDER_TEMPLATE = """
<!doctype html>
<html lang="{{ current_locale.replace('_', '-') }}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ _('Bill of Materials') }} | {{ _('OpenPartsLibrary Admin') }}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='bootstrap-5.3.3-dist/css/bootstrap.min.css') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='bootstrap-icons-1.11.3/font/bootstrap-icons.min.css') }}">
    <style>
        body { background: #f8f9fa; }
        .bom-card { background: white; border: 1px solid #dee2e6; border-radius: 6px; }
        .bom-list-scroll { min-height: 0; overflow: auto; background: white; }
        .bom-list-header { border-top: 1px solid #e0e0e0; border-bottom: 1px solid #e0e0e0; background-color: #f8f9fa; }
        .bom-list-table { border-top: 1px solid lightgray; border-bottom: 1px solid lightgray; }
        .bom-list-row { border-top: 1px solid #e2e6ea; }
        .bom-list-table > .bom-list-row:first-of-type { border-top: 0; }
        .bom-list-main { display: grid; grid-template-columns: 34px minmax(260px, 1fr) 120px 150px 180px; align-items: center; min-height: 36px; gap: 8px; padding-top: 4px; padding-right: 12px; padding-bottom: 4px; cursor: default; }
        .bom-list-main.is-expandable { cursor: pointer; }
        .bom-level-0 { background: #f8f9fa; }
        .bom-level-1 { background: #eef6ff; }
        .bom-level-2 { background: #e3f0ff; }
        .bom-level-3 { background: #d8eaff; }
        .bom-level-4 { background: #cde4ff; }
        .bom-level-5 { background: #c2ddfb; }
        .bom-level-6 { background: #b7d6f6; }
        .bom-level-7 { background: #accff2; }
        .bom-row-bom:hover { background: #dbeafe; }
        .bom-list-meta { color: #6c757d; font-size: 0.9rem; }
        .bom-expand-button { width: 30px; height: 30px; border: 0; background: transparent; color: #042c61; pointer-events: none; }
        .bom-expand-button::before { content: "▸"; display: inline-block; transition: transform 120ms ease; }
        .bom-expand-button[aria-expanded="true"]::before { transform: rotate(90deg); }
        .bom-child-list { display: none; }
        .bom-child-list.is-open { display: block; }
        .bom-kind { color: #6c757d; font-size: 0.82rem; }
        .bom-list-name { display: flex; align-items: baseline; gap: 8px; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .bom-list-number, .bom-list-quantity, .bom-list-cost { color: #5f6b7a; font-size: 0.9rem; }
        .bom-list-actions { display: flex; gap: 6px; justify-content: flex-end; flex-wrap: wrap; }
        .bom-builder-row { display: grid; grid-template-columns: minmax(180px, 1fr) 110px minmax(120px, 0.6fr) 36px; gap: 8px; }
        .opl-admin-header { width: 100%; background: #042c61; color: white; border-bottom: 1px solid #0a3b7a; }
        .opl-admin-header-inner { width: 100%; min-height: 52px; padding: 0 14px; display: flex; align-items: center; justify-content: space-between; gap: 16px; }
        .opl-admin-brand, .opl-admin-brand:hover { display: inline-flex; align-items: center; gap: 8px; color: white; text-decoration: none; font-size: 18px; white-space: nowrap; }
        .opl-admin-brand img { filter: brightness(0.5); }
        .opl-admin-header-right { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; justify-content: flex-end; }
        .opl-admin-navigation { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
        .opl-admin-nav-link, .opl-admin-nav-link:hover { display: inline-flex; align-items: center; min-height: 32px; padding: 4px 8px; border: 0; border-radius: 4px; background: transparent; color: white; text-decoration: none; font-size: 0.9rem; }
        .opl-admin-nav-link:hover { background: rgba(255, 255, 255, 0.14); }
        .opl-admin-navigation .dropdown-menu { margin-top: 8px; z-index: 1000; }
        .opl-admin-navigation .dropdown:hover .dropdown-menu, .opl-admin-navigation .dropdown:focus-within .dropdown-menu { display: block; }
        .opl-admin-header-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; justify-content: flex-end; }
        .opl-admin-header-actions a, .opl-admin-header-actions a:hover { color: white; text-decoration: none; font-size: 0.9rem; }
        @media (max-width: 767.98px) {
            .bom-builder-row { grid-template-columns: 1fr; }
            .bom-list-main { grid-template-columns: 34px minmax(0, 1fr) 80px; }
            .bom-list-cost, .bom-list-actions { grid-column: 2 / -1; text-align: left !important; justify-content: flex-start; }
        }
    </style>
</head>
<body>
    {% include 'admin/_header.html' %}
    <main class="container-fluid py-4">
        <div class="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3">
            <div>
                <h1 class="h3 mb-1">{{ _('Edit BOM') if edit_bom else _('Bill of Materials') }}</h1>
                <div class="text-muted">{{ _('Create nested BOMs from library parts and existing BOMs.') }}</div>
            </div>
        </div>

        <section class="bom-card p-3 mb-3">
            <h2 class="h5 mb-3">{{ _('Update BOM') if edit_bom else _('Create BOM') }}</h2>
            <form method="post" action="{{ form_action }}">
                <div class="row g-2 mb-3">
                    {% if edit_bom %}
                    <div class="col-12 col-md-3">
                        <label class="form-label">{{ _('BOM number') }}</label>
                        <div class="form-control-plaintext fw-semibold">{{ edit_bom.number }}</div>
                    </div>
                    {% endif %}
                    <div class="col-12 {{ 'col-md-4' if edit_bom else 'col-md-5' }}">
                        <label class="form-label">{{ _('Name') }}</label>
                        <input class="form-control" name="name" value="{{ edit_bom.name if edit_bom else '' }}" required>
                    </div>
                    <div class="col-12 {{ 'col-md-5' if edit_bom else 'col-md-7' }}">
                        <label class="form-label">{{ _('Description') }}</label>
                        <input class="form-control" name="description" value="{{ edit_bom.description if edit_bom and edit_bom.description else '' }}">
                    </div>
                </div>
                <div class="d-flex align-items-center justify-content-between mb-2">
                    <h3 class="h6 mb-0">{{ _('Items') }}</h3>
                    <button type="button" class="btn btn-outline-secondary btn-sm" onclick="addBomBuilderRow()">{{ _('Add row') }}</button>
                </div>
                <div id="bom-builder-items" class="d-flex flex-column gap-2"></div>
                <datalist id="bom-option-list">
                    {% for option in bom_options %}
                    <option value="{{ option.display_label }}"></option>
                    {% endfor %}
                </datalist>
                <template id="bom-builder-row-template">
                    <div class="bom-builder-row">
                        <div>
                            <input class="form-control form-control-sm bom-item-search" list="bom-option-list" placeholder="{{ _('Search part or BOM') }}" oninput="syncBomSearch(this)">
                            <input type="hidden" name="child_bom_id">
                        </div>
                        <input class="form-control form-control-sm" name="quantity" type="number" min="1" step="1" value="1">
                        <input class="form-control form-control-sm" name="note" placeholder="{{ _('Note') }}">
                        <button type="button" class="btn btn-outline-secondary btn-sm" onclick="this.closest('.bom-builder-row').remove()">×</button>
                    </div>
                </template>
                <div class="mt-3">
                    <button class="btn btn-primary" type="submit">{{ _('Save BOM') if edit_bom else _('Create BOM') }}</button>
                    {% if edit_bom %}
                    <a class="btn btn-outline-secondary" href="{{ url_for('admin_bill_of_materials') }}">{{ _('Cancel') }}</a>
                    {% endif %}
                </div>
            </form>
        </section>

        {% if not edit_bom %}
        <section class="container-fluid p-0 m-0 d-flex flex-column bom-list-scroll">
            <div class="bom-list-header px-3 py-2">
                <h2 class="mb-0 mt-1" style="font-size: x-large;">{{ _('Bill of Materials') }}</h2>
            </div>
            <p class="pb-2 pt-4 m-0 px-3" style="background-color: white;">{{ ngettext('%(num)s BOM was found.', '%(num)s BOMs were found.', boms|length) }}</p>
            <div class="bom-list-table">
                <div class="bom-list-main fw-semibold" style="background: #ffffff;">
                    <span></span>
                    <span>{{ _('Name') }}</span>
                    <span class="text-end">{{ _('Quantity') }}</span>
                    <span class="text-end">{{ _('Total cost') }}</span>
                    <span class="text-end">{{ _('Actions') }}</span>
                </div>
                {% for bom in boms %}
                    {{ render_bom_row(bom, 0)|safe }}
                {% else %}
                <div class="p-3 text-muted">{{ _('No BOMs have been created yet.') }}</div>
                {% endfor %}
            </div>
        </section>
        {% endif %}
    </main>
    <script>
        const bomOptions = {{ bom_options|tojson }};
        const initialItems = {{ initial_items|tojson }};

        function addBomBuilderRow(item = null) {
            const template = document.getElementById("bom-builder-row-template");
            const target = document.getElementById("bom-builder-items");
            const fragment = template.content.cloneNode(true);
            const row = fragment.querySelector(".bom-builder-row");
            if (item) {
                row.querySelector(".bom-item-search").value = item.display_label || "";
                row.querySelector("input[name='child_bom_id']").value = item.child_bom_id || "";
                row.querySelector("input[name='quantity']").value = item.quantity || 1;
                row.querySelector("input[name='note']").value = item.note || "";
            }
            target.appendChild(fragment);
        }

        function syncBomSearch(input) {
            const row = input.closest(".bom-builder-row");
            const hiddenInput = row ? row.querySelector("input[name='child_bom_id']") : null;
            if (!hiddenInput) {
                return;
            }
            const match = bomOptions.find((option) => option.display_label === input.value);
            hiddenInput.value = match ? match.id : "";
        }

        function toggleBomChildren(button) {
            const row = button.closest(".bom-list-main");
            const target = row ? row.nextElementSibling : null;
            if (!target) {
                return;
            }
            const isOpen = target.classList.toggle("is-open");
            button.setAttribute("aria-expanded", isOpen ? "true" : "false");
        }

        function toggleBomChildrenForRow(event, childrenId) {
            if (event.target.closest("a, button, form, input, select, textarea")) {
                return;
            }
            const button = event.currentTarget.querySelector(".bom-expand-button");
            if (button) {
                toggleBomChildren(button);
            }
        }

        document.addEventListener("DOMContentLoaded", () => {
            if (initialItems.length) {
                initialItems.forEach((item) => addBomBuilderRow(item));
            } else {
                addBomBuilderRow();
            }
        });
    </script>
</body>
</html>
"""


def render_bom_row(bom, depth=0, visited=None, relation_quantity=None):
    visited = set(visited or set())
    children_id = f"bom-children-{bom.id}-{depth}"
    child_rows = []
    if bom.id not in visited:
        next_visited = visited | {bom.id}
        for item in sorted(bom.children, key=lambda child: (child.position, child.id)):
            child_rows.append(render_bom_item_row(item, depth + 1, next_visited))

    can_expand = bool(child_rows)
    expand_button = (
        f'<button class="bom-expand-button" type="button" aria-expanded="false" aria-controls="{children_id}" aria-label="{escape(_("Expand BOM"))}"></button>'
        if can_expand
        else '<span class="d-inline-block" style="width:30px;"></span>'
    )
    number = escape(bom.number or "")
    kind = _("Part") if bom.is_part_wrapper else _("BOM")
    number_label = f'<span class="bom-list-number">{number}</span>' if number else ""
    quantity_label = escape(relation_quantity) if relation_quantity is not None else "-"
    children = f'<div id="{children_id}" class="bom-child-list">{"".join(child_rows)}</div>' if can_expand else ""
    row_click = f' onclick="toggleBomChildrenForRow(event, \'{children_id}\')"' if can_expand else ""
    actions = ""
    if bom.is_part_wrapper and bom.component:
        actions = f"""
            <div class="bom-list-actions">
                <a class="btn btn-sm btn-outline-secondary" href="{url_for("component_view", uuid=bom.component.uuid)}" onclick="event.stopPropagation()" title="{escape(_("Part details"))}" aria-label="{escape(_("Part details"))}"><i class="bi bi-box-arrow-up-right"></i></a>
            </div>
        """
    elif depth == 0 and not bom.is_part_wrapper:
        actions = f"""
            <div class="bom-list-actions">
                <a class="btn btn-sm btn-outline-secondary" href="{url_for("bom_download", bom_id=bom.id)}" onclick="event.stopPropagation()" title="{escape(_("Download"))}" aria-label="{escape(_("Download"))}"><i class="bi bi-download"></i></a>
                <a class="btn btn-sm btn-outline-secondary" href="{url_for("admin_edit_bom", bom_id=bom.id)}" onclick="event.stopPropagation()" title="{escape(_("Modify BOM"))}" aria-label="{escape(_("Modify BOM"))}"><i class="bi bi-pencil-square"></i></a>
                <form method="post" action="{url_for("admin_copy_bom", bom_id=bom.id)}" onclick="event.stopPropagation()">
                    <button class="btn btn-sm btn-outline-secondary" type="submit" title="{escape(_("Copy"))}" aria-label="{escape(_("Copy"))}"><i class="bi bi-copy"></i></button>
                </form>
            </div>
        """
    else:
        actions = '<span></span>'
    return f"""
    <div class="bom-list-row">
        <div class="bom-list-main {'bom-row-part' if bom.is_part_wrapper else 'bom-row-bom'} bom-level-{min(depth, 7)} {'is-expandable' if can_expand else ''}" style="padding-left: {12 + (depth * 22)}px !important;"{row_click}>
            {expand_button}
            <div class="bom-list-name">
                {number_label}
                <span class="fw-semibold">{escape(bom.name)}</span>
                <span class="bom-list-meta">{escape(kind)}</span>
            </div>
            <div class="text-end bom-list-quantity">{quantity_label}</div>
            <div class="text-end bom-list-cost">{escape(format_bom_cost(bom))}</div>
            {actions}
        </div>
        {children}
    </div>
    """


def render_bom_item_row(item, depth, visited):
    quantity = item.quantity.normalize() if item.quantity else 1
    return render_bom_row(item.child_bom, depth, visited, quantity)


def bom_form_items_from_request():
    item_ids = request.form.getlist("child_bom_id")
    quantities = request.form.getlist("quantity")
    notes = request.form.getlist("note")
    return [
        {
            "child_bom_id": item_id,
            "quantity": quantities[index] if index < len(quantities) else 1,
            "note": notes[index] if index < len(notes) else "",
        }
        for index, item_id in enumerate(item_ids)
        if item_id
    ]


def initial_bom_items(bom, bom_options):
    labels_by_id = {option["id"]: option["display_label"] for option in bom_options}
    return [
        {
            "child_bom_id": item.child_bom_id,
            "display_label": labels_by_id.get(item.child_bom_id, ""),
            "quantity": str(item.quantity.normalize() if item.quantity else 1),
            "note": item.note or "",
        }
        for item in sorted(bom.children, key=lambda child: (child.position, child.id))
    ]


def register_bom_admin_routes(app, session):
    if "admin_bill_of_materials" in app.view_functions:
        return

    @app.route("/admin/bill-of-materials", methods=["GET", "POST"])
    def admin_bill_of_materials():
        ensure_part_boms(session)
        if request.method == "POST":
            items = bom_form_items_from_request()
            if request.form.get("name", "").strip():
                create_bom(
                    session,
                    request.form.get("name"),
                    request.form.get("description", ""),
                    items,
                )
            return redirect(url_for("admin_bill_of_materials"))

        return render_template_string(
            BOM_BUILDER_TEMPLATE,
            boms=get_created_boms(session),
            bom_options=get_bom_options(session),
            edit_bom=None,
            form_action=url_for("admin_bill_of_materials"),
            initial_items=[],
            render_bom_row=render_bom_row,
        )

    @app.route("/admin/bill-of-materials/<int:bom_id>/copy", methods=["POST"])
    def admin_copy_bom(bom_id):
        ensure_part_boms(session)
        bom = session.query(BillOfMaterials).filter_by(id=bom_id, is_part_wrapper=False).first()
        if bom is None:
            return _("BOM not found."), 404
        copied_bom = copy_bom(session, bom)
        return redirect(url_for("admin_edit_bom", bom_id=copied_bom.id))

    @app.route("/admin/bill-of-materials/<int:bom_id>/edit", methods=["GET", "POST"])
    def admin_edit_bom(bom_id):
        ensure_part_boms(session)
        bom = session.query(BillOfMaterials).filter_by(id=bom_id, is_part_wrapper=False).first()
        if bom is None:
            return _("BOM not found."), 404
        if request.method == "POST":
            if request.form.get("name", "").strip():
                update_bom(
                    session,
                    bom,
                    request.form.get("name"),
                    request.form.get("description", ""),
                    bom_form_items_from_request(),
                )
            return redirect(url_for("admin_bill_of_materials"))

        bom_options = [
            option for option in get_bom_options(session)
            if option["id"] != bom.id
        ]
        return render_template_string(
            BOM_BUILDER_TEMPLATE,
            boms=[],
            bom_options=bom_options,
            edit_bom=bom,
            form_action=url_for("admin_edit_bom", bom_id=bom.id),
            initial_items=initial_bom_items(bom, bom_options),
            render_bom_row=render_bom_row,
        )


def setup_admin(app, session):
    register_bom_admin_routes(app, session)

    if Admin is None or ModelView is None:
        return setup_fallback_admin(app, session)

    class DownloadEventAdminView(ModelView):
        can_create = False
        can_edit = False
        can_delete = False
        column_default_sort = ("date_downloaded", True)
        column_list = (
            "date_downloaded",
            "download_type",
            "component_number",
            "component_name",
            "file_name",
            "downloaded_filename",
            "quantity",
            "remote_addr",
        )
        column_searchable_list = (
            "download_type",
            "component_number",
            "component_name",
            "file_name",
            "downloaded_filename",
            "remote_addr",
        )
        column_filters = ("download_type", "date_downloaded", "component_number")

    class ComponentAdminView(ModelView):
        column_labels = {
            "unit_price": lazy_gettext("Estimated unit price"),
        }

    class DownloadsDashboardIndexView(AdminIndexView):
        @expose("/")
        def index(self):
            data = get_download_dashboard_data(session, request.args.get("timeframe", "30d"))
            return render_template_string(
                DOWNLOAD_DASHBOARD_TEMPLATE,
                data=data,
                dashboard_url=url_for(".index"),
                admin_home_url=url_for("admin.index"),
            )

    try:
        admin = Admin(app, name=lazy_gettext("OpenPartsLibrary Admin"), template_mode="bootstrap4", url="/admin", index_view=DownloadsDashboardIndexView(name=lazy_gettext("Downloads Dashboard"), endpoint="admin", url="/admin"))
    except TypeError:
        admin = Admin(app, name=lazy_gettext("OpenPartsLibrary Admin"), url="/admin", index_view=DownloadsDashboardIndexView(name=lazy_gettext("Downloads Dashboard"), endpoint="admin", url="/admin"))
    admin.add_view(ComponentAdminView(Component, session, name=lazy_gettext("Parts"), category=lazy_gettext("Library")))
    admin.add_view(ModelView(File, session, name=lazy_gettext("Files"), category=lazy_gettext("Library")))
    admin.add_view(ModelView(Supplier, session, name=lazy_gettext("Suppliers"), category=lazy_gettext("Library")))
    admin.add_view(ModelView(Material, session, name=lazy_gettext("Materials"), category=lazy_gettext("Library")))
    admin.add_view(ModelView(ComponentComponent, session, name=lazy_gettext("Part relations"), category=lazy_gettext("Library")))
    admin.add_view(ModelView(BillOfMaterials, session, name=lazy_gettext("BOM records"), category=lazy_gettext("Library")))
    admin.add_view(ModelView(BillOfMaterialsItem, session, name=lazy_gettext("BOM relations"), category=lazy_gettext("Library")))
    admin.add_view(DownloadEventAdminView(DownloadEvent, session, name=lazy_gettext("Download events"), category=lazy_gettext("Events")))
    return admin


def setup_fallback_admin(app, session):
    model_links = (
        ("Downloads dashboard", None),
        ("Bill of Materials", None),
        ("Parts", Component),
        ("Files", File),
        ("Suppliers", Supplier),
        ("Materials", Material),
        ("Part relations", ComponentComponent),
        ("Download events", DownloadEvent),
    )

    @app.route("/admin")
    def fallback_admin_index():
        rows = [
            {
                "name": _(name),
                "count": session.query(model).count() if model is not None else None,
                "url": (
                    url_for("fallback_admin_downloads_dashboard")
                    if name == "Downloads dashboard"
                    else url_for("admin_bill_of_materials")
                    if name == "Bill of Materials"
                    else url_for("fallback_admin_model", model_name=model.__tablename__)
                ),
            }
            for name, model in model_links
        ]
        return render_template_string(
            """
            <!doctype html>
            <html lang="{{ current_locale.replace('_', '-') }}">
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>{{ _('Admin') }} | OpenPartsLibrary</title>
                <link rel="stylesheet" href="{{ url_for('static', filename='bootstrap-5.3.3-dist/css/bootstrap.min.css') }}">
                <style>
                    .opl-admin-header { width: 100%; background: #042c61; color: white; border-bottom: 1px solid #0a3b7a; }
                    .opl-admin-header-inner { width: 100%; min-height: 52px; padding: 0 14px; display: flex; align-items: center; justify-content: space-between; gap: 16px; }
                    .opl-admin-brand, .opl-admin-brand:hover { display: inline-flex; align-items: center; gap: 8px; color: white; text-decoration: none; font-size: 18px; white-space: nowrap; }
                    .opl-admin-brand img { filter: brightness(0.5); }
                    .opl-admin-header-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; justify-content: flex-end; }
                    .opl-admin-header-actions a, .opl-admin-header-actions a:hover { color: white; text-decoration: none; font-size: 0.9rem; }
                </style>
            </head>
            <body class="bg-light">
                {% include 'admin/_header.html' %}
                <main class="container-fluid py-4">
                    <div class="d-flex align-items-center justify-content-between mb-3">
                        <h1 class="h3 mb-0">{{ _('OpenPartsLibrary Admin') }}</h1>
                        <a class="btn btn-outline-secondary btn-sm" href="{{ url_for('components') }}">{{ _('Back to app') }}</a>
                    </div>
                    <div class="alert alert-warning">
                        {{ _('Flask-Admin is not installed in this Python environment, so this fallback admin is read-only.') }}
                        {{ _('Install Flask-Admin from requirements.txt for full editing features.') }}
                    </div>
                    <div class="list-group">
                        {% for row in rows %}
                        <a class="list-group-item list-group-item-action d-flex justify-content-between align-items-center" href="{{ row.url }}">
                            <span>{{ row.name }}</span>
                            {% if row.count is not none %}
                            <span class="badge text-bg-primary rounded-pill">{{ row.count }}</span>
                            {% endif %}
                        </a>
                        {% endfor %}
                    </div>
                </main>
            </body>
            </html>
            """,
            rows=rows,
        )

    @app.route("/admin/downloads-dashboard")
    def fallback_admin_downloads_dashboard():
        data = get_download_dashboard_data(session, request.args.get("timeframe", "30d"))
        return render_template_string(
            DOWNLOAD_DASHBOARD_TEMPLATE,
            data=data,
            dashboard_url=url_for("fallback_admin_downloads_dashboard"),
            admin_home_url=url_for("fallback_admin_index"),
        )

    @app.route("/admin/<model_name>")
    def fallback_admin_model(model_name):
        models_by_table = {
            model.__tablename__: (name, model)
            for name, model in model_links
            if model is not None
        }
        model_info = models_by_table.get(model_name)
        if model_info is None:
            return _("Admin model not found."), 404

        name, model = model_info
        columns = [column.name for column in model.__table__.columns]
        column_labels = {
            "unit_price": _("Estimated unit price"),
        }
        records = session.query(model).limit(200).all()
        return render_template_string(
            """
            <!doctype html>
            <html lang="{{ current_locale.replace('_', '-') }}">
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>{{ name }} | OpenPartsLibrary Admin</title>
                <link rel="stylesheet" href="{{ url_for('static', filename='bootstrap-5.3.3-dist/css/bootstrap.min.css') }}">
                <style>
                    .opl-admin-header { width: 100%; background: #042c61; color: white; border-bottom: 1px solid #0a3b7a; }
                    .opl-admin-header-inner { width: 100%; min-height: 52px; padding: 0 14px; display: flex; align-items: center; justify-content: space-between; gap: 16px; }
                    .opl-admin-brand, .opl-admin-brand:hover { display: inline-flex; align-items: center; gap: 8px; color: white; text-decoration: none; font-size: 18px; white-space: nowrap; }
                    .opl-admin-brand img { filter: brightness(0.5); }
                    .opl-admin-header-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; justify-content: flex-end; }
                    .opl-admin-header-actions a, .opl-admin-header-actions a:hover { color: white; text-decoration: none; font-size: 0.9rem; }
                </style>
            </head>
            <body class="bg-light">
                {% include 'admin/_header.html' %}
                <main class="container-fluid py-4">
                    <div class="d-flex align-items-center justify-content-between mb-3">
                        <h1 class="h3 mb-0">{{ name }}</h1>
                        <a class="btn btn-outline-secondary btn-sm" href="{{ url_for('fallback_admin_index') }}">{{ _('Admin home') }}</a>
                    </div>
                    <div class="table-responsive bg-white border">
                        <table class="table table-sm table-striped mb-0">
                            <thead>
                                <tr>
                                    {% for column in columns %}
                                    <th>{{ column_labels.get(column, column) }}</th>
                                    {% endfor %}
                                </tr>
                            </thead>
                            <tbody>
                                {% for record in records %}
                                <tr>
                                    {% for column in columns %}
                                    <td>{{ record|attr(column) }}</td>
                                    {% endfor %}
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                    <p class="text-muted mt-2 mb-0">{{ _('Showing up to 200 rows.') }}</p>
                </main>
            </body>
            </html>
            """,
            name=name,
            columns=columns,
            column_labels=column_labels,
            records=records,
        )

    return {"fallback": True}
