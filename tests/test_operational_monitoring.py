import functools
from textwrap import dedent
from unittest.mock import MagicMock, patch

import lkml
import pytest

from generator.dashboards import OperationalMonitoringDashboard
from generator.explores import OperationalMonitoringExplore
from generator.views import OperationalMonitoringView

from .utils import print_and_test


class MockDryRun:
    """Mock dryrun.DryRun."""

    def __init__(
        self,
        client,
        use_cloud_function,
        id_token,
        sql=None,
        project=None,
        dataset=None,
        table=None,
    ):
        self.sql = sql
        self.project = project
        self.dataset = dataset
        self.table = table
        self.use_cloud_function = use_cloud_function
        self.client = client
        self.id_token = id_token

    def get_table_schema(self):
        """Mock dryrun.DryRun.get_table_schema"""
        return [
            {"name": "client_id", "type": "STRING"},
            {"name": "build_id", "type": "STRING"},
            {"name": "cores_count", "type": "STRING"},
            {"name": "os", "type": "STRING"},
            {"name": "branch", "type": "STRING"},
            {"name": "metric", "type": "STRING"},
            {"name": "statistic", "type": "STRING"},
            {"name": "point", "type": "FLOAT"},
            {"name": "lower", "type": "FLOAT"},
            {"name": "upper", "type": "FLOAT"},
            {"name": "parameter", "type": "FLOAT"},
        ]


@pytest.fixture()
def operational_monitoring_view():
    return OperationalMonitoringView(
        "operational_monitoring",
        "fission",
        [
            {
                "table": "moz-fx-data-shared-prod.operational_monitoring.bug_123_test_statistics",
                "xaxis": "build_id",
                "dimensions": {
                    "cores_count": {
                        "default": "4",
                        "options": ["4", "1"],
                    },
                    "os": {
                        "default": "Windows",
                        "options": ["Windows", "Linux"],
                    },
                },
            }
        ],
    )


@pytest.fixture()
@patch("generator.views.lookml_utils.DryRun", MagicMock)
def operational_monitoring_explore(tmp_path, operational_monitoring_view):
    mock_dryrun = functools.partial(MockDryRun, None, False, None)
    (tmp_path / "fission.view.lkml").write_text(
        lkml.dump(operational_monitoring_view.to_lookml(None, dryrun=mock_dryrun))
    )
    return OperationalMonitoringExplore(
        "fission",
        {"base_view": "fission"},
        tmp_path,
        {
            "branches": ["enabled", "disabled"],
            "dimensions": {
                "cores_count": {
                    "default": "4",
                    "options": ["4", "1"],
                },
                "os": {
                    "default": "Windows",
                    "options": ["Windows", "Linux"],
                },
            },
            "summaries": [
                {"metric": "GC_MS", "statistic": "mean"},
                {"metric": "GC_MS_CONTENT", "statistic": "percentile"},
            ],
            "xaxis": "build_id",
        },
    )


@pytest.fixture()
def operational_monitoring_dashboard():
    return OperationalMonitoringDashboard(
        "Fission",
        "fission",
        "newspaper",
        "operational_monitoring",
        [
            {
                "table": "moz-fx-data-shared-prod.operational_monitoring.bug_123_test_statistics",
                "explore": "fission",
                "branches": ["enabled", "disabled"],
                "dimensions": {
                    "cores_count": {
                        "default": "4",
                        "options": ["4", "1"],
                    },
                    "os": {
                        "default": "Windows",
                        "options": ["Windows", "Linux"],
                    },
                },
                "xaxis": "build_id",
                "summaries": [
                    {"metric": "GC_MS", "statistic": "mean"},
                    {"metric": "GC_MS_CONTENT", "statistic": "percentile"},
                ],
            },
        ],
    )


def test_view_from_dict(operational_monitoring_view):
    actual = OperationalMonitoringView.from_dict(
        "operational_monitoring",
        "fission",
        {
            "type": "operational_monitoring_view",
            "tables": [
                {
                    "table": "moz-fx-data-shared-prod.operational_monitoring.bug_123_test_statistics",
                    "xaxis": "build_id",
                    "dimensions": {
                        "cores_count": {
                            "default": "4",
                            "options": ["4", "1"],
                        },
                        "os": {
                            "default": "Windows",
                            "options": ["Windows", "Linux"],
                        },
                    },
                }
            ],
        },
    )

    assert actual == operational_monitoring_view


@patch("generator.views.lookml_utils.DryRun", MockDryRun)
def test_view_lookml(operational_monitoring_view):
    expected = {
        "views": [
            {
                "dimensions": [
                    {
                        "name": "build_id",
                        "sql": "PARSE_DATE('%Y%m%d', "
                        "CAST(${TABLE}.build_id AS STRING))",
                        "type": "date",
                        "datatype": "date",
                        "convert_tz": "no",
                    },
                    {"name": "branch", "sql": "${TABLE}.branch", "type": "string"},
                    {
                        "name": "cores_count",
                        "sql": "${TABLE}.cores_count",
                        "type": "string",
                    },
                    {"name": "metric", "sql": "${TABLE}.metric", "type": "string"},
                    {"name": "os", "sql": "${TABLE}.os", "type": "string"},
                    {
                        "name": "parameter",
                        "sql": "${TABLE}.parameter",
                        "type": "number",
                    },
                    {
                        "name": "statistic",
                        "sql": "${TABLE}.statistic",
                        "type": "string",
                    },
                ],
                "name": "fission",
                "sql_table_name": "moz-fx-data-shared-prod.operational_monitoring.bug_123_test_statistics",
                "measures": [
                    {"name": "point", "sql": "${TABLE}.point", "type": "sum"},
                    {"name": "upper", "sql": "${TABLE}.upper", "type": "sum"},
                    {"name": "lower", "sql": "${TABLE}.lower", "type": "sum"},
                ],
            }
        ]
    }
    mock_dryrun = functools.partial(MockDryRun, None, False, None)
    actual = operational_monitoring_view.to_lookml(None, dryrun=mock_dryrun)
    print(actual)

    print_and_test(expected=expected, actual=actual)


def test_explore_lookml(operational_monitoring_explore):
    expected = [
        {
            "always_filter": {"filters": [{"branch": "enabled, disabled"}]},
            "name": "fission",
            "hidden": "yes",
        }
    ]

    actual = operational_monitoring_explore.to_lookml(None)
    print_and_test(expected=expected, actual=actual)


def test_dashboard_lookml(operational_monitoring_dashboard):
    expected = dedent(
        """\
- dashboard: fission
  title: Fission
  layout: newspaper
  preferred_viewer: dashboards-next

  elements:
  - title: Gc Ms
    name: Gc Ms_mean
    note_state: expanded
    note_display: above
    note_text: Mean
    explore: fission
    type: looker_line
    fields: [
      fission.build_id,
      fission.branch,
      fission.point
    ]
    pivots: [
      fission.branch
    ]
    filters:
      fission.metric: 'GC_MS'
      fission.statistic: mean
    row: 0
    col: 0
    width: 12
    height: 8
    field_x: fission.build_id
    field_y: fission.point
    log_scale: false
    ci_lower: fission.lower
    ci_upper: fission.upper
    show_grid: true
    listen:
      Date: fission.build_id
      Cores Count: fission.cores_count
      Os: fission.os

    enabled: "#3FE1B0"
    disabled: "#0060E0"
    defaults_version: 0
  - title: Gc Ms Content
    name: Gc Ms Content_percentile
    note_state: expanded
    note_display: above
    note_text: Percentile
    explore: fission
    type: "ci-line-chart"
    fields: [
      fission.build_id,
      fission.branch,
      fission.upper,
      fission.lower,
      fission.point
    ]
    pivots: [
      fission.branch
    ]
    filters:
      fission.metric: 'GC_MS_CONTENT'
      fission.statistic: percentile
    row: 0
    col: 12
    width: 12
    height: 8
    field_x: fission.build_id
    field_y: fission.point
    log_scale: false
    ci_lower: fission.lower
    ci_upper: fission.upper
    show_grid: true
    listen:
      Date: fission.build_id
      Percentile: fission.parameter
      Cores Count: fission.cores_count
      Os: fission.os

    enabled: "#3FE1B0"
    disabled: "#0060E0"
    defaults_version: 0

  filters:
  - name: Date
    title: Date
    type: field_filter
    allow_multiple_values: true
    required: false
    ui_config:
      type: advanced
      display: popover
    model: operational_monitoring
    explore: fission
    listens_to_filters: []
    field: fission.build_id

  - name: Percentile
    title: Percentile
    type: field_filter
    default_value: '50'
    allow_multiple_values: false
    required: true
    ui_config:
      type: advanced
      display: popover
    model: operational_monitoring
    explore: fission
    listens_to_filters: []
    field: fission.parameter

  - title: Cores Count
    name: Cores Count
    type: string_filter
    default_value: '4'
    allow_multiple_values: false
    required: true
    ui_config:
      type: dropdown_menu
      display: inline
      options:
      - '4'
      - '1'



  - title: Os
    name: Os
    type: string_filter
    default_value: 'Windows'
    allow_multiple_values: false
    required: true
    ui_config:
      type: dropdown_menu
      display: inline
      options:
      - 'Windows'
      - 'Linux'


    """
    )
    actual = operational_monitoring_dashboard.to_lookml()

    print_and_test(expected=expected, actual=dedent(actual))


@pytest.fixture()
def operational_monitoring_dashboard_group_by_dimension():
    return OperationalMonitoringDashboard(
        "Fission",
        "fission",
        "newspaper",
        "operational_monitoring",
        [
            {
                "table": "moz-fx-data-shared-prod.operational_monitoring.bug_123_test_statistics",
                "explore": "fission",
                "branches": ["enabled", "disabled"],
                "dimensions": {
                    "cores_count": {
                        "default": "4",
                        "options": ["4", "1"],
                    },
                    "os": {
                        "default": "Windows",
                        "options": ["Windows", "Linux"],
                    },
                },
                "group_by_dimension": "os",
                "xaxis": "build_id",
                "summaries": [
                    {"metric": "GC_MS", "statistic": "mean"},
                    {"metric": "GC_MS_CONTENT", "statistic": "percentile"},
                ],
            },
        ],
    )


def test_dashboard_lookml_group_by_dimension(
    operational_monitoring_dashboard_group_by_dimension,
):
    expected = dedent(
        """\
- dashboard: fission
  title: Fission
  layout: newspaper
  preferred_viewer: dashboards-next

  elements:
  - title: Gc Ms - By os
    name: Gc Ms - By os_mean
    note_state: expanded
    note_display: above
    note_text: Mean
    explore: fission
    type: looker_line
    fields: [
      fission.build_id,
      fission.branch,
      fission.point
    ]
    pivots: [
      fission.branch, fission.os
    ]
    filters:
      fission.metric: 'GC_MS'
      fission.statistic: mean
    row: 0
    col: 0
    width: 12
    height: 8
    field_x: fission.build_id
    field_y: fission.point
    log_scale: false
    ci_lower: fission.lower
    ci_upper: fission.upper
    show_grid: true
    listen:
      Date: fission.build_id
      Cores Count: fission.cores_count
      Os: fission.os

    enabled: "#3FE1B0"
    disabled: "#0060E0"
    defaults_version: 0
  - title: Gc Ms Content - By os
    name: Gc Ms Content - By os_percentile
    note_state: expanded
    note_display: above
    note_text: Percentile
    explore: fission
    type: "ci-line-chart"
    fields: [
      fission.build_id,
      fission.branch,
      fission.upper,
      fission.lower,
      fission.point
    ]
    pivots: [
      fission.branch, fission.os
    ]
    filters:
      fission.metric: 'GC_MS_CONTENT'
      fission.statistic: percentile
    row: 0
    col: 12
    width: 12
    height: 8
    field_x: fission.build_id
    field_y: fission.point
    log_scale: false
    ci_lower: fission.lower
    ci_upper: fission.upper
    show_grid: true
    listen:
      Date: fission.build_id
      Percentile: fission.parameter
      Cores Count: fission.cores_count
      Os: fission.os

    enabled: "#3FE1B0"
    disabled: "#0060E0"
    defaults_version: 0

  filters:
  - name: Date
    title: Date
    type: field_filter
    allow_multiple_values: true
    required: false
    ui_config:
      type: advanced
      display: popover
    model: operational_monitoring
    explore: fission
    listens_to_filters: []
    field: fission.build_id

  - name: Percentile
    title: Percentile
    type: field_filter
    default_value: '50'
    allow_multiple_values: false
    required: true
    ui_config:
      type: advanced
      display: popover
    model: operational_monitoring
    explore: fission
    listens_to_filters: []
    field: fission.parameter

  - title: Cores Count
    name: Cores Count
    type: string_filter
    default_value: '4'
    allow_multiple_values: false
    required: true
    ui_config:
      type: dropdown_menu
      display: inline
      options:
      - '4'
      - '1'



  - title: Os
    name: Os
    type: string_filter
    default_value: 'Linux,Windows'
    allow_multiple_values: true
    required: true
    ui_config:
      type: advanced
      display: inline
      options:
      - 'Linux'
      - 'Windows'


    """
    )
    actual = operational_monitoring_dashboard_group_by_dimension.to_lookml()

    print_and_test(expected=expected, actual=dedent(actual))
