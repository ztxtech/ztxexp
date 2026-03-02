"""可选外部平台适配器。"""

from __future__ import annotations

from typing import Any

from ztxexp.types import MetricEvent, RunContext, RunMetadata


class MlflowTracker:
    """MLflow 追踪器（可选依赖）。"""

    def __init__(
        self,
        tracking_uri: str | None = None,
        experiment_name: str | None = None,
        run_name: str | None = None,
    ):
        self.tracking_uri = tracking_uri
        self.experiment_name = experiment_name
        self.run_name = run_name
        self._started = False

    def _mlflow(self):
        try:
            import mlflow

            return mlflow
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "mlflow is required for MlflowTracker. Install with: pip install ztxexp[mlflow]"
            ) from exc

    def on_run_start(self, ctx: RunContext, meta: RunMetadata) -> None:
        mlflow = self._mlflow()
        if self.tracking_uri:
            mlflow.set_tracking_uri(self.tracking_uri)
        if self.experiment_name or meta.experiment_name:
            mlflow.set_experiment(self.experiment_name or str(meta.experiment_name))
        mlflow.start_run(run_name=self.run_name or ctx.run_id)
        self._started = True
        mlflow.log_params(
            {
                k: v
                for k, v in ctx.config.items()
                if isinstance(v, (str, int, float, bool))
            }
        )
        mlflow.set_tags(
            {
                "run_id": ctx.run_id,
                "group": meta.group or "",
                "parent_run_id": meta.parent_run_id or "",
            }
        )

    def on_metric(self, ctx: RunContext, event: MetricEvent) -> None:
        if not self._started:
            return
        mlflow = self._mlflow()
        mlflow.log_metrics(event.metrics, step=event.step)

    def on_run_end(self, ctx: RunContext, summary: dict[str, object]) -> None:
        if not self._started:
            return
        mlflow = self._mlflow()
        status = summary.get("status")
        if status is not None:
            mlflow.set_tag("status", str(status))
        mlflow.end_run()
        self._started = False


class WandbTracker:
    """Weights & Biases 追踪器（可选依赖）。"""

    def __init__(self, project: str | None = None, entity: str | None = None, **kwargs: Any):
        self.project = project
        self.entity = entity
        self.kwargs = kwargs
        self._run = None

    def _wandb(self):
        try:
            import wandb

            return wandb
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "wandb is required for WandbTracker. Install with: pip install ztxexp[wandb]"
            ) from exc

    def on_run_start(self, ctx: RunContext, meta: RunMetadata) -> None:
        wandb = self._wandb()
        self._run = wandb.init(
            project=self.project,
            entity=self.entity,
            config=ctx.config,
            name=ctx.run_id,
            reinit=True,
            **self.kwargs,
        )
        if self._run is not None:
            if meta.experiment_name:
                self._run.summary["experiment_name"] = meta.experiment_name
            if meta.group:
                self._run.summary["group"] = meta.group

    def on_metric(self, ctx: RunContext, event: MetricEvent) -> None:
        if self._run is None:
            return
        wandb = self._wandb()
        wandb.log(dict(event.metrics), step=event.step)

    def on_run_end(self, ctx: RunContext, summary: dict[str, object]) -> None:
        if self._run is None:
            return
        self._run.summary.update(summary)
        self._run.finish()
        self._run = None
