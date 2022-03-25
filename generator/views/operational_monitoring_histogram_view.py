"""Class to describe an Operational Monitoring Histogram View."""

from textwrap import dedent
from typing import Any, Dict, Optional

from . import lookml_utils
from .operational_monitoring_view import OperationalMonitoringView

ALLOWED_DIMENSIONS = {
    "branch",
    "probe",
    "histogram__VALUES__key",
    "histogram__VALUES__value",
}


class OperationalMonitoringHistogramView(OperationalMonitoringView):
    """A view on a scalar operational monitoring table."""

    type: str = "operational_monitoring_histogram_view"

    def _percentile_measure(self, percentile_ci_label) -> Dict[str, str]:
        return {
            "name": percentile_ci_label,
            "type": "number",
            "sql": dedent(
                f"""
                `moz-fx-data-shared-prod`.udf_js.jackknife_percentile_ci(
                    {{% parameter percentile_conf %}},
                    STRUCT(
                        mozfun.hist.merge(
                          ARRAY_AGG(
                            ${{TABLE}}.histogram IGNORE NULLS
                          )
                        ).values AS values
                    )
                ).{percentile_ci_label}
            """
            ),
        }

    def to_lookml(self, bq_client, v1_name: Optional[str]) -> Dict[str, Any]:
        """Get this view as LookML."""
        if len(self.tables) == 0:
            raise Exception((f"Operational Monitoring view {self.name} has no tables"))

        reference_table = self.tables[0]["table"]
        all_dimensions = lookml_utils._generate_dimensions(bq_client, reference_table)

        filtered_dimensions = [
            d
            for d in all_dimensions
            if d["name"] in ALLOWED_DIMENSIONS
            or d["name"] in self.tables[0].get("dimensions", {}).keys()
        ]
        self.dimensions.extend(filtered_dimensions)

        return {
            "views": [
                {
                    "name": self.name,
                    "sql_table_name": reference_table,
                    "dimensions": self.dimensions,
                    "parameters": self.parameters,
                    "measures": [
                        self._percentile_measure(label)
                        for label in self.percentile_ci_labels
                    ],
                }
            ]
        }
