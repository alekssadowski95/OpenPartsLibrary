import json
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

from openpartslibrary.boms import copy_bom, create_bom, ensure_part_boms, format_bom_cost, get_bom_options, get_created_boms, replace_bom_items, update_bom
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
        .opl-admin-navigation .dropdown-menu { margin-top: 0; z-index: 1000; }
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
        .bom-list-toolbar { min-height: 58px; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 14px; margin: -1.5rem -12px 0; background: white; border-bottom: 1px solid #d7dde5; }
        .bom-list-toolbar-title { min-width: 0; }
        .bom-list-toolbar h1 { font-size: 1.25rem; margin: 0; }
        .bom-list-toolbar-subtitle { color: #667085; font-size: 0.88rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .bom-list-toolbar-actions { display: flex; align-items: center; justify-content: flex-end; gap: 8px; flex-wrap: wrap; }
        .bom-list-scroll { min-height: 0; overflow: auto; background: white; }
        .bom-list-header { border-top: 1px solid #e0e0e0; border-bottom: 1px solid #e0e0e0; background-color: #f8f9fa; }
        .bom-list-table { border-top: 1px solid lightgray; border-bottom: 1px solid lightgray; }
        .bom-list-row { border-top: 1px solid #e2e6ea; }
        .bom-list-table > .bom-list-row:first-of-type { border-top: 0; }
        .bom-list-main { display: grid; grid-template-columns: 34px minmax(220px, 1fr) 90px 130px 250px; align-items: center; min-height: 36px; gap: 8px; padding-top: 4px; padding-right: 12px; padding-bottom: 4px; cursor: default; }
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
        .bom-list-icon { flex: 0 0 auto; color: #042c61; font-size: 1rem; line-height: 1; }
        .bom-list-icon-part { color: #0d6efd; }
        .bom-list-number, .bom-list-quantity, .bom-list-cost { color: #5f6b7a; font-size: 0.9rem; }
        .bom-list-actions { display: flex; gap: 6px; justify-content: flex-end; flex-wrap: nowrap; white-space: nowrap; }
        .bom-builder-table { border: 1px solid #dee2e6; background: white; }
        .bom-builder-header,
        .bom-builder-row { display: grid; grid-template-columns: minmax(220px, 1fr) 120px 44px; align-items: center; gap: 8px; }
        .bom-builder-header { min-height: 36px; padding: 6px 10px; background: #f8f9fa; border-bottom: 1px solid #dee2e6; color: #5f6b7a; font-size: 0.86rem; font-weight: 600; }
        .bom-builder-row { min-height: 44px; padding: 6px 10px; border-top: 1px solid #e2e6ea; }
        .bom-builder-items > .bom-builder-row:first-child { border-top: 0; }
        .bom-builder-remove-button { width: 32px; height: 32px; padding: 0; display: inline-flex; align-items: center; justify-content: center; }
        .opl-admin-header { width: 100%; background: #042c61; color: white; border-bottom: 1px solid #0a3b7a; }
        .opl-admin-header-inner { width: 100%; min-height: 52px; padding: 0 14px; display: flex; align-items: center; justify-content: space-between; gap: 16px; }
        .opl-admin-brand, .opl-admin-brand:hover { display: inline-flex; align-items: center; gap: 8px; color: white; text-decoration: none; font-size: 18px; white-space: nowrap; }
        .opl-admin-brand img { filter: brightness(0.5); }
        .opl-admin-header-right { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; justify-content: flex-end; }
        .opl-admin-navigation { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
        .opl-admin-nav-link, .opl-admin-nav-link:hover { display: inline-flex; align-items: center; min-height: 32px; padding: 4px 8px; border: 0; border-radius: 4px; background: transparent; color: white; text-decoration: none; font-size: 0.9rem; }
        .opl-admin-nav-link:hover { background: rgba(255, 255, 255, 0.14); }
        .opl-admin-navigation .dropdown-menu { margin-top: 0; z-index: 1000; }
        .opl-admin-navigation .dropdown:hover .dropdown-menu, .opl-admin-navigation .dropdown:focus-within .dropdown-menu { display: block; }
        .opl-admin-header-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; justify-content: flex-end; }
        .opl-admin-header-actions a, .opl-admin-header-actions a:hover { color: white; text-decoration: none; font-size: 0.9rem; }
        @media (max-width: 767.98px) {
            .bom-list-toolbar { align-items: flex-start; flex-direction: column; }
            .bom-list-toolbar-actions { justify-content: flex-start; }
            .bom-builder-row { grid-template-columns: 1fr; }
            .bom-builder-header { display: none; }
            .bom-list-main { grid-template-columns: 34px minmax(0, 1fr) 80px; }
            .bom-list-cost, .bom-list-actions { grid-column: 2 / -1; text-align: right !important; justify-content: flex-end; }
        }
    </style>
</head>
<body>
    {% include 'admin/_header.html' %}
    <main class="container-fluid py-4">
        {% if edit_bom %}
        <div class="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3">
            <div>
                <h1 class="h3 mb-1">{{ _('Edit BOM') }}</h1>
                <div class="text-muted">{{ _('Create nested BOMs from library parts and existing BOMs.') }}</div>
            </div>
            <a class="btn btn-outline-secondary" href="{{ node_editor_url }}"><i class="bi bi-diagram-3 me-1" aria-hidden="true"></i>{{ _('Node editor') }}</a>
        </div>

        <section class="bom-card p-3 mb-3">
            <h2 class="h5 mb-3">{{ _('Update BOM') }}</h2>
            <form method="post" action="{{ form_action }}">
                <div class="row g-2 mb-3">
                    <div class="col-12 col-md-3">
                        <label class="form-label">{{ _('BOM number') }}</label>
                        <div class="form-control-plaintext fw-semibold">{{ edit_bom.number }}</div>
                    </div>
                    <div class="col-12 col-md-4">
                        <label class="form-label">{{ _('Name') }}</label>
                        <input id="bom-root-name-input" class="form-control" name="name" value="{{ edit_bom.name }}" required>
                    </div>
                    <div class="col-12 col-md-5">
                        <label class="form-label">{{ _('Description') }}</label>
                        <input class="form-control" name="description" value="{{ edit_bom.description if edit_bom.description else '' }}">
                    </div>
                </div>
                <div class="d-flex align-items-center justify-content-between mb-2">
                    <h3 class="h6 mb-0">{{ _('Items') }}</h3>
                </div>
                <div class="bom-builder-table">
                    <div class="bom-builder-header">
                        <span>{{ _('Item') }}</span>
                        <span>{{ _('Quantity') }}</span>
                        <span></span>
                    </div>
                    <div id="bom-builder-items" class="bom-builder-items"></div>
                </div>
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
                        <button type="button" class="btn btn-outline-secondary bom-builder-remove-button" onclick="removeBomBuilderRow(this.closest('.bom-builder-row'))" title="{{ _('Remove') }}" aria-label="{{ _('Remove') }}"><i class="bi bi-x-lg"></i></button>
                    </div>
                </template>
                <div class="mt-3 d-flex flex-wrap align-items-center gap-2">
                    <button type="button" class="btn btn-outline-secondary" onclick="addBomBuilderRow()"><i class="bi bi-plus-lg me-1" aria-hidden="true"></i>{{ _('Add item') }}</button>
                    <button class="btn btn-primary" type="submit">{{ _('Save BOM') }}</button>
                    <a class="btn btn-outline-secondary" href="{{ url_for('admin_bill_of_materials') }}">{{ _('Cancel') }}</a>
                </div>
            </form>
        </section>
        {% else %}
        <div class="bom-list-toolbar">
            <div class="bom-list-toolbar-title">
                <h1>{{ _('Bill of Materials') }}</h1>
                <div class="bom-list-toolbar-subtitle">{{ _('Create nested BOMs from library parts and existing BOMs.') }}</div>
            </div>
            <div class="bom-list-toolbar-actions">
                <a class="btn btn-primary" href="{{ node_editor_url }}"><i class="bi bi-plus-lg me-1" aria-hidden="true"></i>{{ _('New BOM') }}</a>
            </div>
        </div>
        <section class="container-fluid p-0 m-0 d-flex flex-column bom-list-scroll">
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

        function removeBomBuilderRow(row) {
            if (row) {
                row.remove();
            }
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
            if (!document.getElementById("bom-builder-row-template")) {
                return;
            }
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


BOM_NODE_EDITOR_TEMPLATE = """
<!doctype html>
<html lang="{{ current_locale.replace('_', '-') }}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ _('BOM Node Editor') }} | {{ _('OpenPartsLibrary Admin') }}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='bootstrap-5.3.3-dist/css/bootstrap.min.css') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='bootstrap-icons-1.11.3/font/bootstrap-icons.min.css') }}">
    <style>
        html, body { height: 100%; }
        body { min-height: 100%; background: #eef2f6; overflow: hidden; }
        .opl-admin-header { width: 100%; background: #042c61; color: white; border-bottom: 1px solid #0a3b7a; }
        .opl-admin-header-inner { width: 100%; min-height: 52px; padding: 0 14px; display: flex; align-items: center; justify-content: space-between; gap: 16px; }
        .opl-admin-brand, .opl-admin-brand:hover { display: inline-flex; align-items: center; gap: 8px; color: white; text-decoration: none; font-size: 18px; white-space: nowrap; }
        .opl-admin-brand img { filter: brightness(0.5); }
        .opl-admin-header-right { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; justify-content: flex-end; }
        .opl-admin-navigation { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
        .opl-admin-nav-link, .opl-admin-nav-link:hover { display: inline-flex; align-items: center; min-height: 32px; padding: 4px 8px; border: 0; border-radius: 4px; background: transparent; color: white; text-decoration: none; font-size: 0.9rem; }
        .opl-admin-nav-link:hover { background: rgba(255, 255, 255, 0.14); }
        .opl-admin-navigation .dropdown-menu { margin-top: 0; z-index: 1000; }
        .opl-admin-navigation .dropdown:hover .dropdown-menu, .opl-admin-navigation .dropdown:focus-within .dropdown-menu { display: block; }
        .opl-admin-header-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; justify-content: flex-end; }
        .opl-admin-header-actions a, .opl-admin-header-actions a:hover { color: white; text-decoration: none; font-size: 0.9rem; }
        .bom-node-page { height: calc(100vh - 52px); display: flex; flex-direction: column; min-height: 0; }
        .bom-node-toolbar { min-height: 58px; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 14px; background: white; border-bottom: 1px solid #d7dde5; }
        .bom-node-toolbar-title { min-width: 0; }
        .bom-node-toolbar h1 { font-size: 1.25rem; margin: 0; }
        .bom-node-toolbar-subtitle { color: #667085; font-size: 0.88rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .bom-node-toolbar-actions { display: flex; align-items: center; justify-content: flex-end; gap: 8px; flex-wrap: wrap; }
        .bom-node-canvas { position: relative; flex: 1 1 auto; min-height: 0; overflow: hidden; background-color: #eef2f6; background-image: radial-gradient(#cbd5df 1px, transparent 1px); background-size: 20px 20px; cursor: grab; touch-action: none; }
        .bom-node-canvas.is-panning { cursor: grabbing; }
        .bom-node-world { position: absolute; left: 0; top: 0; width: 1600px; min-height: 900px; transform-origin: 0 0; }
        .bom-node-links { position: absolute; inset: 0; width: 1600px; height: 900px; overflow: visible; pointer-events: none; }
        .bom-node-link { stroke: #6b7f97; stroke-width: 2; fill: none; }
        .bom-node-card { position: absolute; width: 220px; background: white; border: 1px solid #cfd7e2; border-radius: 6px; box-shadow: 0 8px 18px rgba(16, 24, 40, 0.12); font-size: 0.82rem; cursor: default; }
        .bom-node-card-root { width: 250px; border-color: #8fb4dc; }
        .bom-node-header { display: flex; align-items: center; gap: 7px; min-height: 32px; padding: 7px 38px 7px 9px; border-bottom: 1px solid #e1e7ef; background: #f8fafc; color: #1f2937; position: relative; }
        .bom-node-header i { flex: 0 0 auto; color: #042c61; }
        .bom-node-title { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 600; }
        .bom-node-body { padding: 9px; }
        .bom-node-body .form-label { margin-bottom: 3px; color: #5f6b7a; font-size: 0.72rem; }
        .bom-node-field-row { display: grid; grid-template-columns: minmax(0, 1fr) 62px; gap: 8px; align-items: end; }
        .bom-node-readonly-value { min-height: 28px; padding: 4px 0; color: #1f2937; font-size: 0.82rem; overflow-wrap: anywhere; }
        .bom-node-readonly-muted { color: #667085; }
        .bom-node-card-readonly { background: #f8fafc; }
        .bom-node-source-switch { display: grid; grid-template-columns: 1fr 1fr; margin-bottom: 8px; border-bottom: 1px solid #d7dde5; }
        .bom-node-source-tab { min-height: 30px; padding: 4px 6px; border: 0; border-bottom: 2px solid transparent; background: transparent; color: #5f6b7a; font-size: 0.76rem; font-weight: 600; }
        .bom-node-source-tab:hover { color: #042c61; background: #f8fafc; }
        .bom-node-source-tab.is-active { color: #042c61; border-bottom-color: #0d6efd; background: white; }
        .bom-node-combobox { position: relative; }
        .bom-node-combobox .form-control { padding-right: 58px; }
        .bom-node-body .form-control::placeholder { color: #9aa6b2; opacity: 1; }
        .bom-node-selection-clear,
        .bom-node-dropdown-toggle { position: absolute; top: 0; width: 28px; height: 31px; display: inline-flex; align-items: center; justify-content: center; padding: 0; border: 0; background: transparent; color: #667085; }
        .bom-node-selection-clear { right: 28px; }
        .bom-node-dropdown-toggle { right: 0; }
        .bom-node-selection-clear:hover,
        .bom-node-dropdown-toggle:hover { color: #042c61; }
        .bom-node-options { position: absolute; z-index: 30; left: 0; right: 0; top: calc(100% + 3px); display: none; max-height: 190px; overflow: auto; background: white; border: 1px solid #cfd7e2; border-radius: 4px; box-shadow: 0 10px 22px rgba(16, 24, 40, 0.16); }
        .bom-node-options.is-open { display: block; }
        .bom-node-option { width: 100%; display: flex; align-items: center; gap: 7px; min-height: 30px; padding: 5px 8px; border: 0; background: white; color: #1f2937; font-size: 0.78rem; text-align: left; }
        .bom-node-option:hover, .bom-node-option:focus { background: #eef6ff; outline: 0; }
        .bom-node-option-empty { padding: 7px 8px; color: #7a8794; font-size: 0.78rem; }
        .bom-node-delete { position: absolute; top: 4px; right: 5px; width: 26px; height: 26px; display: inline-flex; align-items: center; justify-content: center; padding: 0; border-color: transparent; background: transparent; }
        .bom-node-add-child { position: absolute; top: 50%; right: -42px; transform: translateY(-50%); width: 32px; height: 32px; display: inline-flex; align-items: center; justify-content: center; padding: 0; border-radius: 999px; box-shadow: 0 6px 14px rgba(16, 24, 40, 0.16); }
        .bom-node-empty { position: absolute; color: #667085; background: rgba(255, 255, 255, 0.9); border: 1px dashed #aab8c7; border-radius: 6px; padding: 12px 14px; display: flex; align-items: center; gap: 10px; }
        .bom-node-empty .btn { width: 32px; height: 32px; display: inline-flex; align-items: center; justify-content: center; padding: 0; border-radius: 999px; }
        .bom-node-zoom { position: absolute; right: 14px; bottom: 14px; display: flex; gap: 6px; padding: 6px; background: rgba(255, 255, 255, 0.92); border: 1px solid #d7dde5; border-radius: 6px; box-shadow: 0 8px 18px rgba(16, 24, 40, 0.12); }
        .bom-node-zoom .btn { width: 34px; height: 34px; display: inline-flex; align-items: center; justify-content: center; padding: 0; }
        .bom-node-modal-backdrop { position: fixed; inset: 0; z-index: 1100; display: none; align-items: center; justify-content: center; background: rgba(15, 23, 42, 0.46); padding: 16px; }
        .bom-node-modal-backdrop.is-open { display: flex; }
        .bom-node-modal { width: min(440px, 100%); background: white; border-radius: 6px; border: 1px solid #d7dde5; box-shadow: 0 22px 50px rgba(16, 24, 40, 0.22); }
        .bom-node-modal-header, .bom-node-modal-body, .bom-node-modal-footer { padding: 14px 16px; }
        .bom-node-modal-header { border-bottom: 1px solid #e6ebf1; font-weight: 600; }
        .bom-node-modal-footer { display: flex; justify-content: flex-end; gap: 8px; border-top: 1px solid #e6ebf1; }
        @media (max-width: 767.98px) {
            body { overflow: auto; }
            .bom-node-page { height: auto; min-height: calc(100vh - 52px); }
            .bom-node-toolbar { align-items: flex-start; flex-direction: column; }
            .bom-node-toolbar-actions { justify-content: flex-start; }
            .bom-node-canvas { min-height: 720px; }
        }
    </style>
</head>
<body>
    {% include 'admin/_header.html' %}
    <form id="bom-node-form" class="bom-node-page" method="post" action="{{ form_action }}">
        <div class="bom-node-toolbar">
            <div class="bom-node-toolbar-title">
                <h1>{{ _('BOM Node Editor') }}</h1>
                <div class="bom-node-toolbar-subtitle">
                    {% if edit_bom %}{{ edit_bom.number }} - {{ edit_bom.name }}{% else %}{{ _('Create a BOM from existing BOMs and parts.') }}{% endif %}
                </div>
            </div>
            <div class="bom-node-toolbar-actions">
                <button id="clear-node-editor-button" type="button" class="btn btn-outline-secondary" onclick="openClearModal()">{{ _('Clear') }}</button>
                <button class="btn btn-primary" type="submit">{{ _('Save BOM') if edit_bom else _('Create BOM') }}</button>
            </div>
        </div>
        <div id="node-hidden-inputs"></div>
        <datalist id="bom-option-list">
            {% for option in bom_options %}
            <option value="{{ option.display_label }}"></option>
            {% endfor %}
        </datalist>
        <div id="bom-node-canvas" class="bom-node-canvas">
            <div id="bom-node-world" class="bom-node-world"></div>
            <div class="bom-node-zoom" aria-label="{{ _('Zoom controls') }}">
                <button type="button" class="btn btn-outline-secondary btn-sm" onclick="zoomBy(1.15)" title="{{ _('Zoom in') }}" aria-label="{{ _('Zoom in') }}"><i class="bi bi-plus-lg"></i></button>
                <button type="button" class="btn btn-outline-secondary btn-sm" onclick="zoomBy(0.87)" title="{{ _('Zoom out') }}" aria-label="{{ _('Zoom out') }}"><i class="bi bi-dash-lg"></i></button>
                <button type="button" class="btn btn-outline-secondary btn-sm" onclick="resetView()" title="{{ _('Reset view') }}" aria-label="{{ _('Reset view') }}"><i class="bi bi-aspect-ratio"></i></button>
            </div>
        </div>
        <div id="delete-node-modal" class="bom-node-modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="delete-node-modal-title">
            <div class="bom-node-modal">
                <div id="delete-node-modal-title" class="bom-node-modal-header">{{ _('Delete node') }}</div>
                <div class="bom-node-modal-body">{{ _('This node has child nodes. Deleting it will also remove those nested items from this BOM structure.') }}</div>
                <div class="bom-node-modal-footer">
                    <button type="button" class="btn btn-outline-secondary" onclick="closeDeleteModal()">{{ _('Cancel') }}</button>
                    <button type="button" class="btn btn-danger" onclick="confirmDeleteNode()">{{ _('Delete') }}</button>
                </div>
            </div>
        </div>
        <div id="clear-node-editor-modal" class="bom-node-modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="clear-node-editor-modal-title">
            <div class="bom-node-modal">
                <div id="clear-node-editor-modal-title" class="bom-node-modal-header">{{ _('Clear BOM draft') }}</div>
                <div class="bom-node-modal-body">{{ _('This will remove all nodes from the current editor draft and keep only the root node. The local draft saved in this browser will also be deleted.') }}</div>
                <div class="bom-node-modal-footer">
                    <button type="button" class="btn btn-outline-secondary" onclick="closeClearModal()">{{ _('Cancel') }}</button>
                    <button type="button" class="btn btn-danger" onclick="confirmClearEditor()">{{ _('Clear') }}</button>
                </div>
            </div>
        </div>
    </form>
    <script>
        const bomOptions = {{ bom_options|tojson }};
        const initialItems = {{ initial_items|tojson }};
        const newBomLabel = {{ _('New BOM')|tojson }};
        const selectItemLabel = {{ _('Select part or BOM')|tojson }};
        const noNodesLabel = {{ _('Add BOMs or parts.')|tojson }};
        const draftStorageKey = {{ draft_storage_key|tojson }};
        let rootName = {{ (edit_bom.name if edit_bom else '')|tojson }};
        let rootDescription = {{ (edit_bom.description if edit_bom and edit_bom.description else '')|tojson }};
        let nodes = initialItems.length ? initialItems.map((item) => normalizeNode(item)) : [];
        let scale = 1;
        let panX = 30;
        let panY = 30;
        let isPanning = false;
        let isSubmitting = false;
        let measuredNodeHeights = {};
        let panStart = { x: 0, y: 0, panX: 0, panY: 0 };
        let pendingDeletePath = null;
        const nodeTop = 80;
        const nodeVerticalGap = 34;
        const nodeHorizontalPitch = 302;
        const firstChildNodeX = 402;
        const rootNodeWidth = 250;
        const childNodeWidth = 220;
        const nodeLinkY = 23;
        const nodeAddButtonOffset = 42;
        const nodeAddButtonWidth = 32;
        const nodeConnectorRightGap = 20;
        const nodeConnectorTargetGap = 20;
        const nodeConnectorVerticalGap = 18;

        function normalizeNode(item = {}) {
            return {
                child_bom_id: item.child_bom_id || "",
                display_label: item.display_label || "",
                source_type: item.source_type || "existing",
                readonly: Boolean(item.readonly),
                new_bom_name: item.new_bom_name || "",
                new_bom_description: item.new_bom_description || "",
                quantity: item.quantity || "1",
                children: Array.isArray(item.children) ? item.children.map((child) => normalizeNode(child)) : [],
            };
        }

        function getNode(path) {
            let branch = nodes;
            let node = null;
            for (const index of path) {
                node = branch[index];
                if (!node) {
                    return null;
                }
                if (!Array.isArray(node.children)) {
                    node.children = [];
                }
                branch = node.children;
            }
            return node;
        }

        function getBranch(path) {
            if (!path.length) {
                return nodes;
            }
            const parent = getNode(path);
            if (parent && !Array.isArray(parent.children)) {
                parent.children = [];
            }
            return parent ? parent.children : nodes;
        }

        function pathExpression(path) {
            return `[${path.join(",")}]`;
        }

        function pathKey(path) {
            return path.length ? path.join(".") : "root";
        }

        function addBomNode(path = []) {
            const parent = path.length ? getNode(path) : null;
            if (parent && !canNodeHaveChildren(parent)) {
                return;
            }
            getBranch(path).push(normalizeNode());
            renderNodes();
        }

        function requestRemoveBomNode(path) {
            const node = getNode(path);
            if (!node) {
                return;
            }
            if (node.readonly) {
                return;
            }
            if (node.children.length) {
                pendingDeletePath = path;
                document.getElementById("delete-node-modal").classList.add("is-open");
                return;
            }
            removeBomNode(path);
        }

        function removeBomNode(path) {
            const parentPath = path.slice(0, -1);
            const index = path[path.length - 1];
            getBranch(parentPath).splice(index, 1);
            renderNodes();
        }

        function closeDeleteModal() {
            pendingDeletePath = null;
            document.getElementById("delete-node-modal").classList.remove("is-open");
        }

        function confirmDeleteNode() {
            if (pendingDeletePath) {
                removeBomNode(pendingDeletePath);
            }
            closeDeleteModal();
        }

        function openClearModal() {
            const modal = document.getElementById("clear-node-editor-modal");
            modal.classList.add("is-open");
            modal.style.display = "flex";
        }

        function closeClearModal() {
            const modal = document.getElementById("clear-node-editor-modal");
            modal.classList.remove("is-open");
            modal.style.display = "";
        }

        function confirmClearEditor() {
            isSubmitting = true;
            rootName = {{ (edit_bom.name if edit_bom else '')|tojson }};
            rootDescription = {{ (edit_bom.description if edit_bom and edit_bom.description else '')|tojson }};
            nodes = [];
            closeClearModal();
            clearDraft();
            renderNodes();
            frameInitialRootView();
            isSubmitting = false;
            syncHiddenInputs();
        }

        function updateRoot(field, value) {
            if (field === "name") {
                rootName = value;
            } else if (field === "description") {
                rootDescription = value;
            }
            syncHiddenInputs();
        }

        function updateNode(path, field, value) {
            const node = getNode(path);
            if (!node) {
                return;
            }
            if (node.readonly) {
                return;
            }
            const couldHaveChildren = canNodeHaveChildren(node);
            node[field] = value;
            if (field === "display_label") {
                const match = bomOptions.find((option) => option.display_label === value);
                node.child_bom_id = match ? match.id : "";
                if (match) {
                    node.children = [];
                }
            }
            if (field === "display_label" && couldHaveChildren !== canNodeHaveChildren(node)) {
                renderNodes();
                return;
            }
            syncHiddenInputs();
        }

        function setNodeSourceType(path, sourceType) {
            const node = getNode(path);
            if (!node) {
                return;
            }
            if (node.readonly) {
                return;
            }
            node.source_type = sourceType;
            if (sourceType === "new") {
                node.child_bom_id = "";
                node.display_label = "";
            } else {
                node.children = [];
            }
            renderNodes();
        }

        function renderNodeOptions(input, path) {
            const menu = input.closest(".bom-node-combobox")?.querySelector(".bom-node-options");
            if (!menu) {
                return;
            }
            const query = input.value.trim().toLowerCase();
            const matches = bomOptions
                .filter((option) => !query || option.display_label.toLowerCase().includes(query))
                .slice(0, 60);
            if (!matches.length) {
                menu.innerHTML = `<div class="bom-node-option-empty">{{ _('No matching BOMs or parts.') }}</div>`;
            } else {
                menu.innerHTML = matches.map((option) => `
                    <button type="button" class="bom-node-option" data-option-id="${escapeHtml(option.id)}" data-option-label="${escapeHtml(option.display_label)}" onclick="selectNodeOption(this, ${pathExpression(path)})">
                        <i class="bi ${option.is_part_wrapper ? "bi-box-fill text-primary" : "bi-table"}" aria-hidden="true"></i>
                        <span>${escapeHtml(option.display_label)}</span>
                    </button>
                `).join("");
            }
            menu.classList.add("is-open");
        }

        function toggleNodeDropdown(button, path) {
            const wrapper = button.closest(".bom-node-combobox");
            const input = wrapper ? wrapper.querySelector("input") : null;
            const menu = wrapper ? wrapper.querySelector(".bom-node-options") : null;
            if (!input || !menu) {
                return;
            }
            if (menu.classList.contains("is-open")) {
                menu.classList.remove("is-open");
                return;
            }
            renderNodeOptions(input, path);
            input.focus();
        }

        function selectNodeOption(button, path) {
            const wrapper = button.closest(".bom-node-combobox");
            const input = wrapper ? wrapper.querySelector("input") : null;
            const menu = wrapper ? wrapper.querySelector(".bom-node-options") : null;
            const node = getNode(path);
            if (!node) {
                return;
            }
            if (node.readonly) {
                return;
            }
            node.child_bom_id = button.dataset.optionId || "";
            node.display_label = button.dataset.optionLabel || "";
            node.children = [];
            if (input) {
                input.value = node.display_label;
                updateNodeHeader(input, path);
            }
            if (menu) {
                menu.classList.remove("is-open");
            }
            syncHiddenInputs();
            renderNodes();
        }

        function clearNodeSelection(button, path) {
            const wrapper = button.closest(".bom-node-combobox");
            const input = wrapper ? wrapper.querySelector("input") : null;
            const menu = wrapper ? wrapper.querySelector(".bom-node-options") : null;
            const node = getNode(path);
            if (!node) {
                return;
            }
            if (node.readonly) {
                return;
            }
            node.child_bom_id = "";
            node.display_label = "";
            if (input) {
                input.value = "";
                updateNodeHeader(input, path);
            }
            if (menu) {
                menu.classList.remove("is-open");
            }
            syncHiddenInputs();
            renderNodes();
        }

        function closeNodeDropdowns(exceptWrapper = null) {
            document.querySelectorAll(".bom-node-options.is-open").forEach((menu) => {
                if (!exceptWrapper || !exceptWrapper.contains(menu)) {
                    menu.classList.remove("is-open");
                }
            });
        }

        function updateRootTitle(value) {
            const title = document.querySelector(".bom-node-card-root .bom-node-title");
            if (title) {
                const text = value.trim() || newBomLabel;
                title.textContent = text;
                title.title = text;
            }
        }

        function updateNodeHeader(input, path) {
            const card = input.closest(".bom-node-card");
            const title = card ? card.querySelector(".bom-node-title") : null;
            const icon = card ? card.querySelector(".bom-node-header i") : null;
            const node = getNode(path);
            const text = node && node.source_type === "new" ? (node.new_bom_name || newBomLabel) : (input.value || selectItemLabel);
            if (title) {
                title.textContent = text;
                title.title = text;
            }
            if (icon && node) {
                icon.className = `bi ${iconForNode(node)}`;
            }
        }

        function optionForNode(node) {
            if (node.source_type === "new") {
                return null;
            }
            return bomOptions.find((option) => String(option.id) === String(node.child_bom_id)) || null;
        }

        function iconForNode(node) {
            if (node.source_type === "new") {
                return "bi-table";
            }
            const option = optionForNode(node);
            return option && option.is_part_wrapper ? "bi-box-fill text-primary" : "bi-table";
        }

        function canNodeHaveChildren(node) {
            return !node.readonly && node.source_type === "new";
        }

        function syncHiddenInputs() {
            const target = document.getElementById("node-hidden-inputs");
            target.innerHTML = `
                <input type="hidden" name="name" value="${escapeHtml(rootName)}">
                <input type="hidden" name="description" value="${escapeHtml(rootDescription)}">
                <input type="hidden" name="node_tree" value="${escapeHtml(JSON.stringify({ children: nodes }))}">
            `;
            saveDraft();
        }

        function saveDraft() {
            if (isSubmitting) {
                return;
            }
            try {
                window.localStorage.setItem(draftStorageKey, JSON.stringify({
                    rootName,
                    rootDescription,
                    nodes,
                    savedAt: new Date().toISOString(),
                }));
            } catch (error) {
                // Local storage can be unavailable in private or locked-down browser contexts.
            }
        }

        function restoreDraft() {
            try {
                const rawDraft = window.localStorage.getItem(draftStorageKey);
                if (!rawDraft) {
                    return false;
                }
                const draft = JSON.parse(rawDraft);
                if (!draft || typeof draft !== "object") {
                    return false;
                }
                rootName = draft.rootName || "";
                rootDescription = draft.rootDescription || "";
                nodes = Array.isArray(draft.nodes) ? draft.nodes.map((item) => normalizeNode(item)) : [];
                return true;
            } catch (error) {
                return false;
            }
        }

        function clearDraft() {
            try {
                window.localStorage.removeItem(draftStorageKey);
            } catch (error) {
                // Nothing to do if the browser refuses local storage access.
            }
        }

        function nodeCard(node, path, x, y) {
            const title = node.source_type === "new" ? (node.new_bom_name || newBomLabel) : (node.display_label || selectItemLabel);
            const icon = iconForNode(node);
            const expression = pathExpression(path);
            const allowChildren = canNodeHaveChildren(node);
            const readonlyDetails = node.readonly ? `
                        <div class="bom-node-field-row">
                            <div>
                                <label class="form-label">{{ _('Item') }}</label>
                                <div class="bom-node-readonly-value">${escapeHtml(title)}</div>
                            </div>
                            <div>
                                <label class="form-label">{{ _('Quantity') }}</label>
                                <div class="bom-node-readonly-value">${escapeHtml(node.quantity || "1")}</div>
                            </div>
                        </div>
            ` : "";
            return `
                <div class="bom-node-card ${node.readonly ? "bom-node-card-readonly" : ""}" data-node-path="${escapeHtml(pathKey(path))}" style="left:${x}px; top:${y}px;">
                    <div class="bom-node-header">
                        <i class="bi ${icon}" aria-hidden="true"></i>
                        <span class="bom-node-title" title="${escapeHtml(title)}">${escapeHtml(title)}</span>
                        ${node.readonly ? "" : `<button type="button" class="btn btn-outline-secondary bom-node-delete" onclick="requestRemoveBomNode(${expression})" title="{{ _('Remove') }}" aria-label="{{ _('Remove') }}"><i class="bi bi-x-lg"></i></button>`}
                    </div>
                    <div class="bom-node-body">
                        ${node.readonly ? readonlyDetails : `
                        <div class="bom-node-source-switch" role="group" aria-label="{{ _('Node type') }}">
                            <button type="button" class="bom-node-source-tab ${node.source_type !== "new" ? "is-active" : ""}" onclick="setNodeSourceType(${expression}, 'existing')">{{ _('Select') }}</button>
                            <button type="button" class="bom-node-source-tab ${node.source_type === "new" ? "is-active" : ""}" onclick="setNodeSourceType(${expression}, 'new')">{{ _('New') }}</button>
                        </div>
                        ${node.source_type === "new" ? `
                            <div class="bom-node-field-row mb-2">
                                <div>
                                    <label class="form-label">{{ _('BOM name') }}</label>
                                    <input class="form-control form-control-sm" value="${escapeHtml(node.new_bom_name || "")}" placeholder="{{ _('Enter BOM name...') }}" oninput="updateNode(${expression}, 'new_bom_name', this.value); updateNodeHeader(this, ${expression});">
                                </div>
                                <div>
                                    <label class="form-label">{{ _('Quantity') }}</label>
                                    <input class="form-control form-control-sm" type="number" min="1" step="1" value="${escapeHtml(node.quantity || "1")}" oninput="updateNode(${expression}, 'quantity', this.value)">
                                </div>
                            </div>
                            <label class="form-label">{{ _('Description') }}</label>
                            <input class="form-control form-control-sm mb-2" value="${escapeHtml(node.new_bom_description || "")}" placeholder="{{ _('Enter description...') }}" oninput="updateNode(${expression}, 'new_bom_description', this.value)">
                        ` : `
                            <div class="bom-node-field-row">
                                <div>
                                    <label class="form-label">{{ _('Item') }}</label>
                                    <div class="bom-node-combobox">
                                        <input class="form-control form-control-sm" value="${escapeHtml(node.display_label || "")}" placeholder="{{ _('Enter BOM / Part name...') }}" onfocus="renderNodeOptions(this, ${expression})" oninput="updateNode(${expression}, 'display_label', this.value); updateNodeHeader(this, ${expression}); renderNodeOptions(this, ${expression});">
                                        <button type="button" class="bom-node-selection-clear" onclick="clearNodeSelection(this, ${expression})" title="{{ _('Clear selection') }}" aria-label="{{ _('Clear selection') }}"><i class="bi bi-x-lg"></i></button>
                                        <button type="button" class="bom-node-dropdown-toggle" onclick="toggleNodeDropdown(this, ${expression})" title="{{ _('Show options') }}" aria-label="{{ _('Show options') }}"><i class="bi bi-chevron-down"></i></button>
                                        <div class="bom-node-options"></div>
                                    </div>
                                </div>
                                <div>
                                    <label class="form-label">{{ _('Quantity') }}</label>
                                    <input class="form-control form-control-sm" type="number" min="1" step="1" value="${escapeHtml(node.quantity || "1")}" oninput="updateNode(${expression}, 'quantity', this.value)">
                                </div>
                            </div>
                        `}
                        `}
                    </div>
                    ${allowChildren ? `<button type="button" class="btn btn-primary bom-node-add-child" onclick="addBomNode(${expression})" title="{{ _('Add child node') }}" aria-label="{{ _('Add child node') }}"><i class="bi bi-plus-lg"></i></button>` : ""}
                </div>
            `;
        }

        function estimatedNodeHeight(node, isRoot = false) {
            const key = isRoot ? "root" : null;
            if (key && measuredNodeHeights[key]) {
                return measuredNodeHeights[key];
            }
            if (isRoot) {
                return {{ 190 if edit_bom else 150 }};
            }
            return node.source_type === "new" ? 300 : 205;
        }

        function nodeLayoutHeight(node, path) {
            const measuredHeight = measuredNodeHeights[pathKey(path)];
            if (measuredHeight) {
                return measuredHeight;
            }
            if (node.readonly) {
                return 120;
            }
            return node.source_type === "new" ? 205 : 135;
        }

        function layoutBranch(branch, depth, positions, links, levelCursors, connectorCursors, parent = null, path = []) {
            if (!branch.length) {
                return;
            }
            const nodeHeights = branch.map((node, index) => nodeLayoutHeight(node, path.concat(index)));
            const groupHeight = nodeHeights.reduce((total, height) => total + height, 0) + (nodeVerticalGap * Math.max(0, branch.length - 1));
            const parentHeight = parent?.height || 0;
            const preferredStartY = parent ? parent.y + (parentHeight / 2) - (groupHeight / 2) : nodeTop;
            let cursorY = Math.max(levelCursors[depth] ?? -Infinity, preferredStartY);
            if (parent) {
                const lastNodeTop = cursorY + groupHeight - nodeHeights[nodeHeights.length - 1];
                const parentAnchorY = parent.y + nodeLinkY;
                const firstAnchorY = cursorY + nodeLinkY;
                const lastAnchorY = lastNodeTop + nodeLinkY;
                const connectorMinY = Math.min(parentAnchorY, firstAnchorY, lastAnchorY);
                const minAllowedConnectorY = connectorCursors[depth] ?? -Infinity;
                if (connectorMinY < minAllowedConnectorY) {
                    cursorY += minAllowedConnectorY - connectorMinY;
                }
            }
            if (parent) {
                const centeredParentY = cursorY + (groupHeight / 2) - (parentHeight / 2);
                if (centeredParentY > parent.y) {
                    parent.y = centeredParentY;
                    if (parent.depth !== undefined) {
                        levelCursors[parent.depth] = Math.max(levelCursors[parent.depth] ?? -Infinity, parent.y + parent.height + nodeVerticalGap);
                    }
                }
            }
            branch.forEach((node, index) => {
                const currentPath = path.concat(index);
                const nodeHeight = nodeHeights[index];
                const x = firstChildNodeX + (depth * nodeHorizontalPitch);
                const y = cursorY;
                const width = childNodeWidth;
                const key = pathKey(currentPath);
                const position = { node, path: currentPath, key, x, y, width, height: nodeHeight, depth };
                positions.push(position);
                if (parent) {
                    links.push({ fromKey: parent.key, toKey: key });
                }
                layoutBranch(node.children, depth + 1, positions, links, levelCursors, connectorCursors, position, currentPath);
                cursorY = position.y + nodeHeight + nodeVerticalGap;
                levelCursors[depth] = Math.max(levelCursors[depth] ?? -Infinity, cursorY);
            });
            if (parent) {
                const firstNodeTop = cursorY - groupHeight - nodeVerticalGap;
                const lastNodeTop = cursorY - nodeVerticalGap - nodeHeights[nodeHeights.length - 1];
                const parentAnchorY = parent.y + nodeLinkY;
                const firstAnchorY = firstNodeTop + nodeLinkY;
                const lastAnchorY = lastNodeTop + nodeLinkY;
                connectorCursors[depth] = Math.max(parentAnchorY, firstAnchorY, lastAnchorY) + nodeConnectorVerticalGap;
            }
        }

        function connectorPathsForGroup(from, children) {
            if (!from || !children.length) {
                return "";
            }
            const fromX = from.x + from.width;
            const fromY = from.y + nodeLinkY;
            const minToX = Math.min(...children.map((child) => child.x));
            const preferredTrunkX = fromX + nodeAddButtonOffset + nodeConnectorRightGap;
            const trunkX = Math.min(minToX - nodeConnectorTargetGap, preferredTrunkX);
            const childYs = children.map((child) => child.y + nodeLinkY);
            const minY = Math.min(fromY, ...childYs);
            const maxY = Math.max(fromY, ...childYs);
            const parentPath = `<path class="bom-node-link" d="M ${fromX} ${fromY} H ${trunkX}"></path>`;
            const trunkPath = `<path class="bom-node-link" d="M ${trunkX} ${minY} V ${maxY}"></path>`;
            const childPaths = children.map((child) => {
                const childY = child.y + nodeLinkY;
                return `<path class="bom-node-link" d="M ${trunkX} ${childY} H ${child.x}"></path>`;
            }).join("");
            return `${parentPath}${trunkPath}${childPaths}`;
        }

        function captureMeasuredNodeHeights() {
            const nextHeights = {};
            document.querySelectorAll(".bom-node-card").forEach((card) => {
                const key = card.dataset.nodePath || "root";
                nextHeights[key] = Math.ceil(card.offsetHeight || 0);
            });
            const changed = JSON.stringify(nextHeights) !== JSON.stringify(measuredNodeHeights);
            measuredNodeHeights = nextHeights;
            return changed;
        }

        function renderNodes(allowRemeasure = true) {
            const world = document.getElementById("bom-node-world");
            const rootTitle = rootName.trim() || newBomLabel;
            const rootX = 70;
            const positions = [];
            const linkRows = [];
            const rootHeight = estimatedNodeHeight(null, true);
            let rootY = nodeTop;
            const rootPosition = { key: "root", x: rootX, y: rootY, width: rootNodeWidth, height: rootHeight };
            layoutBranch(nodes, 0, positions, linkRows, {}, {}, rootPosition);
            rootY = rootPosition.y;
            const minY = Math.min(rootY, ...positions.map((position) => position.y));
            if (minY < nodeTop) {
                const offsetY = nodeTop - minY;
                rootY += offsetY;
                rootPosition.y = rootY;
                positions.forEach((position) => {
                    position.y += offsetY;
                });
            }
            const positionsByKey = {
                root: rootPosition,
            };
            positions.forEach((position) => {
                positionsByKey[position.key] = position;
            });
            const maxX = Math.max(rootX, ...positions.map((position) => position.x));
            const maxY = Math.max(rootY + rootHeight, ...positions.map((position) => position.y + position.height));
            let contentHeight = Math.max(900, maxY + 120);
            let contentWidth = Math.max(1600, maxX + 380);
            const linksByParent = linkRows.reduce((groups, link) => {
                if (!groups[link.fromKey]) {
                    groups[link.fromKey] = [];
                }
                groups[link.fromKey].push(link.toKey);
                return groups;
            }, {});
            let links = Object.entries(linksByParent).map(([fromKey, toKeys]) => {
                const from = positionsByKey[fromKey];
                const children = toKeys.map((toKey) => positionsByKey[toKey]).filter(Boolean);
                return connectorPathsForGroup(from, children);
            }).join("");
            let childCards = positions.map((position) => nodeCard(position.node, position.path, position.x, position.y)).join("");
            world.style.minHeight = `${contentHeight}px`;
            world.style.width = `${contentWidth}px`;
            world.innerHTML = `
                <svg class="bom-node-links" style="width:${contentWidth}px; height:${contentHeight}px;" aria-hidden="true">${links}</svg>
                <div class="bom-node-card bom-node-card-root" data-node-path="root" style="left:${rootX}px; top:${rootY}px;">
                    <div class="bom-node-header">
                        <i class="bi bi-table" aria-hidden="true"></i>
                        <span class="bom-node-title" title="${escapeHtml(rootTitle)}">${escapeHtml(rootTitle)}</span>
                    </div>
                    <div class="bom-node-body">
                        {% if edit_bom %}
                        <label class="form-label">{{ _('BOM number') }}</label>
                        <div class="form-control-plaintext py-0 mb-2 fw-semibold">{{ edit_bom.number }}</div>
                        {% endif %}
                        <label class="form-label">{{ _('Name') }}</label>
                        <input id="root-name" class="form-control form-control-sm mb-2" value="${escapeHtml(rootName)}" placeholder="{{ _('Enter BOM name...') }}" required oninput="updateRoot('name', this.value); updateRootTitle(this.value);">
                        <label class="form-label">{{ _('Description') }}</label>
                        <input id="root-description" class="form-control form-control-sm" value="${escapeHtml(rootDescription)}" placeholder="{{ _('Enter description...') }}" oninput="updateRoot('description', this.value)">
                    </div>
                    ${nodes.length ? `<button type="button" class="btn btn-primary bom-node-add-child" onclick="addBomNode([])" title="{{ _('Add child node') }}" aria-label="{{ _('Add child node') }}"><i class="bi bi-plus-lg"></i></button>` : ""}
                </div>
                ${childCards || `<div class="bom-node-empty" style="left:${rootX + 320}px; top:${rootY + 56}px;"><span>${escapeHtml(noNodesLabel)}</span><button type="button" class="btn btn-primary" onclick="addBomNode([])" title="{{ _('Add child node') }}" aria-label="{{ _('Add child node') }}"><i class="bi bi-plus-lg"></i></button></div>`}
            `;
            applyTransform();
            syncHiddenInputs();
            if (allowRemeasure && captureMeasuredNodeHeights()) {
                renderNodes(false);
            }
        }

        function applyTransform() {
            const world = document.getElementById("bom-node-world");
            world.style.transform = `translate(${panX}px, ${panY}px) scale(${scale})`;
        }

        function zoomBy(factor, origin = null) {
            const canvas = document.getElementById("bom-node-canvas");
            const rect = canvas.getBoundingClientRect();
            const oldScale = scale;
            const nextScale = Math.min(2.2, Math.max(0.35, scale * factor));
            const point = origin || { x: rect.width / 2, y: rect.height / 2 };
            const worldX = (point.x - panX) / oldScale;
            const worldY = (point.y - panY) / oldScale;
            scale = nextScale;
            panX = point.x - (worldX * scale);
            panY = point.y - (worldY * scale);
            applyTransform();
        }

        function resetView() {
            frameInitialRootView();
        }

        function fitTreeView() {
            const canvas = document.getElementById("bom-node-canvas");
            const cards = Array.from(document.querySelectorAll(".bom-node-card"));
            if (!canvas || !cards.length) {
                scale = 1;
                panX = 30;
                panY = 30;
                applyTransform();
                return;
            }

            const padding = 56;
            const bounds = cards.reduce((box, card) => {
                const left = Number.parseFloat(card.style.left || "0");
                const top = Number.parseFloat(card.style.top || "0");
                const width = card.offsetWidth || (card.classList.contains("bom-node-card-root") ? rootNodeWidth : childNodeWidth);
                const height = card.offsetHeight || 220;
                return {
                    minX: Math.min(box.minX, left),
                    minY: Math.min(box.minY, top),
                    maxX: Math.max(box.maxX, left + width + 54),
                    maxY: Math.max(box.maxY, top + height),
                };
            }, { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity });

            const treeWidth = Math.max(1, bounds.maxX - bounds.minX);
            const treeHeight = Math.max(1, bounds.maxY - bounds.minY);
            const availableWidth = Math.max(1, canvas.clientWidth - (padding * 2));
            const availableHeight = Math.max(1, canvas.clientHeight - (padding * 2));
            scale = Math.min(1, Math.max(0.35, Math.min(availableWidth / treeWidth, availableHeight / treeHeight)));
            panX = ((canvas.clientWidth - (treeWidth * scale)) / 2) - (bounds.minX * scale);
            panY = ((canvas.clientHeight - (treeHeight * scale)) / 2) - (bounds.minY * scale);
            applyTransform();
        }

        function centerRootVertically() {
            const canvas = document.getElementById("bom-node-canvas");
            const root = document.querySelector(".bom-node-card-root");
            if (!canvas || !root) {
                return;
            }
            const rootTop = Number.parseFloat(root.style.top || "0");
            const rootHeight = root.offsetHeight || 190;
            panY = (canvas.clientHeight / 2) - rootTop - (rootHeight / 2);
            applyTransform();
        }

        function frameInitialRootView() {
            const canvas = document.getElementById("bom-node-canvas");
            const root = document.querySelector(".bom-node-card-root");
            if (!canvas || !root) {
                return;
            }
            const rootLeft = Number.parseFloat(root.style.left || "0");
            const rootTop = Number.parseFloat(root.style.top || "0");
            const rootWidth = root.offsetWidth || rootNodeWidth;
            const rootHeight = root.offsetHeight || 190;
            scale = Math.min(1.25, Math.max(0.35, canvas.clientHeight / (rootHeight * 6)));
            panX = Math.max(48, (canvas.clientWidth * 0.2) - (rootLeft * scale));
            panY = (canvas.clientHeight / 2) - ((rootTop + (rootHeight / 2)) * scale);
            applyTransform();
        }

        function escapeHtml(value) {
            return String(value ?? "")
                .replaceAll("&", "&amp;")
                .replaceAll("<", "&lt;")
                .replaceAll(">", "&gt;")
                .replaceAll('"', "&quot;")
                .replaceAll("'", "&#039;");
        }

        document.addEventListener("DOMContentLoaded", () => {
            const restoredDraft = restoreDraft();
            renderNodes();
            frameInitialRootView();
            const canvas = document.getElementById("bom-node-canvas");
            canvas.addEventListener("wheel", (event) => {
                if (event.target.closest(".bom-node-options")) {
                    return;
                }
                event.preventDefault();
                const rect = canvas.getBoundingClientRect();
                zoomBy(event.deltaY < 0 ? 1.08 : 0.92, { x: event.clientX - rect.left, y: event.clientY - rect.top });
            }, { passive: false });
            canvas.addEventListener("pointerdown", (event) => {
                if (event.target.closest(".bom-node-card, .bom-node-zoom, .bom-node-empty, button, input, select, textarea, a")) {
                    return;
                }
                isPanning = true;
                canvas.classList.add("is-panning");
                canvas.setPointerCapture(event.pointerId);
                panStart = { x: event.clientX, y: event.clientY, panX, panY };
            });
            canvas.addEventListener("pointermove", (event) => {
                if (!isPanning) {
                    return;
                }
                panX = panStart.panX + event.clientX - panStart.x;
                panY = panStart.panY + event.clientY - panStart.y;
                applyTransform();
            });
            canvas.addEventListener("pointerup", () => {
                isPanning = false;
                canvas.classList.remove("is-panning");
            });
            canvas.addEventListener("pointercancel", () => {
                isPanning = false;
                canvas.classList.remove("is-panning");
            });
            document.getElementById("bom-node-form").addEventListener("submit", () => {
                isSubmitting = true;
                syncHiddenInputs();
                clearDraft();
            });
            document.getElementById("clear-node-editor-button").addEventListener("click", (event) => {
                event.preventDefault();
                openClearModal();
            });
            document.addEventListener("click", (event) => {
                const wrapper = event.target.closest(".bom-node-combobox");
                closeNodeDropdowns(wrapper);
            });
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
    row_icon = (
        '<i class="bi bi-box-fill bom-list-icon bom-list-icon-part" aria-hidden="true"></i>'
        if bom.is_part_wrapper
        else '<i class="bi bi-table bom-list-icon" aria-hidden="true"></i>'
    )
    number_label = f'<span class="bom-list-number">{number}</span>' if number else ""
    quantity_label = escape(relation_quantity) if relation_quantity is not None else "-"
    children = f'<div id="{children_id}" class="bom-child-list">{"".join(child_rows)}</div>' if can_expand else ""
    row_click = f' onclick="toggleBomChildrenForRow(event, \'{children_id}\')"' if can_expand else ""
    actions = ""
    if bom.is_part_wrapper and bom.component:
        actions = f"""
            <div class="bom-list-actions">
                <a class="btn btn-sm btn-outline-secondary" href="{url_for("component_view", uuid=bom.component.uuid)}" onclick="event.stopPropagation()" title="{escape(_("Part details"))}" aria-label="{escape(_("Part details"))}"><i class="bi bi-eye"></i></a>
            </div>
        """
    elif not bom.is_part_wrapper:
        download_action = (
            f'<a class="btn btn-sm btn-outline-secondary" href="{url_for("bom_download", bom_id=bom.id)}" onclick="event.stopPropagation()" title="{escape(_("Download"))}" aria-label="{escape(_("Download"))}"><i class="bi bi-download"></i></a>'
            if depth == 0
            else ""
        )
        edit_actions = (
            f"""
                <a class="btn btn-sm btn-outline-secondary" href="{url_for("admin_edit_bom_node_editor", bom_id=bom.id)}" onclick="event.stopPropagation()" title="{escape(_("Modify BOM"))}" aria-label="{escape(_("Modify BOM"))}"><i class="bi bi-pencil-square"></i></a>
                <form method="post" action="{url_for("admin_copy_bom", bom_id=bom.id)}" onclick="event.stopPropagation()">
                    <button class="btn btn-sm btn-outline-secondary" type="submit" title="{escape(_("Copy"))}" aria-label="{escape(_("Copy"))}"><i class="bi bi-copy"></i></button>
                </form>
            """
            if depth == 0
            else ""
        )
        actions = f"""
            <div class="bom-list-actions">
                <a class="btn btn-sm btn-outline-secondary" href="{url_for("bom_view", bom_id=bom.id)}" onclick="event.stopPropagation()" title="{escape(_("BOM details"))}" aria-label="{escape(_("BOM details"))}"><i class="bi bi-eye"></i></a>
                {download_action}
                {edit_actions}
            </div>
        """
    else:
        actions = '<span></span>'
    return f"""
    <div class="bom-list-row">
        <div class="bom-list-main {'bom-row-part' if bom.is_part_wrapper else 'bom-row-bom'} bom-level-{min(depth, 7)} {'is-expandable' if can_expand else ''}" style="padding-left: {12 + (depth * 22)}px !important;"{row_click}>
            {expand_button}
            <div class="bom-list-name">
                {row_icon}
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
    return [
        {
            "child_bom_id": item_id,
            "quantity": quantities[index] if index < len(quantities) else 1,
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
        }
        for item in sorted(bom.children, key=lambda child: (child.position, child.id))
    ]


def initial_bom_tree_items(bom, bom_options, visited=None, readonly=False):
    visited = set(visited or set())
    labels_by_id = {option["id"]: option["display_label"] for option in bom_options}
    tree_items = []
    for item in sorted(bom.children, key=lambda child: (child.position, child.id)):
        child_bom = item.child_bom
        children = []
        if child_bom and not child_bom.is_part_wrapper and child_bom.id not in visited:
            children = initial_bom_tree_items(child_bom, bom_options, visited | {bom.id}, readonly=True)
        tree_items.append({
            "child_bom_id": item.child_bom_id,
            "display_label": labels_by_id.get(item.child_bom_id, ""),
            "source_type": "existing",
            "readonly": readonly,
            "new_bom_name": "",
            "new_bom_description": "",
            "quantity": str(item.quantity.normalize() if item.quantity else 1),
            "children": children,
        })
    return tree_items


def node_editor_payload_from_request():
    try:
        payload = json.loads(request.form.get("node_tree") or "{}")
    except (TypeError, ValueError):
        payload = {}
    return payload if isinstance(payload, dict) else {}


def resolve_node_editor_child_bom(session, node):
    if not isinstance(node, dict):
        return None

    if node.get("source_type") == "new":
        name = str(node.get("new_bom_name") or "").strip()
        if not name:
            return None
        return create_bom(
            session,
            name,
            node.get("new_bom_description", ""),
            [],
        )

    child_bom_id = node.get("child_bom_id")
    if not child_bom_id:
        return None
    try:
        return session.query(BillOfMaterials).filter_by(id=int(child_bom_id)).first()
    except (TypeError, ValueError):
        return None


def save_nested_bom_nodes(session, parent_bom, nodes, visited=None):
    visited = set(visited or set())
    if parent_bom is None or parent_bom.id in visited:
        return

    next_visited = visited | {parent_bom.id}
    resolved_items = []
    for node in nodes or []:
        if not isinstance(node, dict):
            continue
        child_bom = resolve_node_editor_child_bom(session, node)
        if child_bom is None or child_bom.id in visited:
            continue
        if node.get("source_type") != "new" or child_bom.is_part_wrapper:
            node["children"] = []
        else:
            save_nested_bom_nodes(session, child_bom, node.get("children", []), next_visited)
        resolved_items.append({
            "child_bom_id": child_bom.id,
            "quantity": node.get("quantity", 1),
        })

    replace_bom_items(session, parent_bom, resolved_items)
    session.flush()


def save_node_editor_bom(session, bom, name, description, payload):
    bom.name = str(name or "").strip()
    bom.description = str(description or "").strip() or None
    save_nested_bom_nodes(session, bom, payload.get("children", []))
    session.commit()
    return bom


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
            node_editor_url=url_for("admin_bom_node_editor"),
            initial_items=[],
            render_bom_row=render_bom_row,
        )

    @app.route("/admin/bill-of-materials/node-editor", methods=["GET", "POST"])
    def admin_bom_node_editor():
        ensure_part_boms(session)
        if request.method == "POST":
            if request.form.get("name", "").strip():
                bom = create_bom(
                    session,
                    request.form.get("name"),
                    request.form.get("description", ""),
                    [],
                )
                save_node_editor_bom(
                    session,
                    bom,
                    request.form.get("name"),
                    request.form.get("description", ""),
                    node_editor_payload_from_request(),
                )
            return redirect(url_for("admin_bill_of_materials"))

        return render_template_string(
            BOM_NODE_EDITOR_TEMPLATE,
            bom_options=get_bom_options(session),
            edit_bom=None,
            form_action=url_for("admin_bom_node_editor"),
            table_editor_url=url_for("admin_bill_of_materials"),
            draft_storage_key="openpartslibrary:bom-node-editor:new",
            initial_items=[],
        )

    @app.route("/admin/bill-of-materials/<int:bom_id>/copy", methods=["POST"])
    def admin_copy_bom(bom_id):
        ensure_part_boms(session)
        bom = session.query(BillOfMaterials).filter_by(id=bom_id, is_part_wrapper=False).first()
        if bom is None:
            return _("BOM not found."), 404
        copied_bom = copy_bom(session, bom)
        return redirect(url_for("admin_edit_bom", bom_id=copied_bom.id))

    @app.route("/admin/bill-of-materials/<int:bom_id>/node-editor", methods=["GET", "POST"])
    def admin_edit_bom_node_editor(bom_id):
        ensure_part_boms(session)
        bom = session.query(BillOfMaterials).filter_by(id=bom_id, is_part_wrapper=False).first()
        if bom is None:
            return _("BOM not found."), 404
        if request.method == "POST":
            if request.form.get("name", "").strip():
                save_node_editor_bom(
                    session,
                    bom,
                    request.form.get("name"),
                    request.form.get("description", ""),
                    node_editor_payload_from_request(),
                )
            return redirect(url_for("admin_bill_of_materials"))

        bom_options = [
            option for option in get_bom_options(session)
            if option["id"] != bom.id
        ]
        return render_template_string(
            BOM_NODE_EDITOR_TEMPLATE,
            bom_options=bom_options,
            edit_bom=bom,
            form_action=url_for("admin_edit_bom_node_editor", bom_id=bom.id),
            table_editor_url=url_for("admin_edit_bom", bom_id=bom.id),
            draft_storage_key=f"openpartslibrary:bom-node-editor:edit:{bom.id}",
            initial_items=initial_bom_tree_items(bom, bom_options),
        )

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
            node_editor_url=url_for("admin_edit_bom_node_editor", bom_id=bom.id),
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
