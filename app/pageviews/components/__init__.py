# app/components/__init__.py
# Expose all components for easy import

from .sidebar import render_sidebar
from .patient_card import patient_card, patient_search_box
from .charts import (
    appointments_bar_chart,
    revenue_line_chart,
    fraud_pie_chart,
    stock_bar_chart,
    daily_metrics_chart
)
