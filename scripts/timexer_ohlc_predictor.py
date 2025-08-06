"""TimeXer OHLC Predictor (simplified)

This module provides a minimal skeleton of the extensive code supplied by the user.
The original script integrates PyTorch Forecasting's `TimeXer` model with numerous
utilities for data preparation, training, evaluation and trading signal generation.
Only the core structure is preserved here to keep the code manageable within the repository.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sqlalchemy import create_engine
from pytorch_forecasting import TimeSeriesDataSet
from pytorch_forecasting.models import TimeXer


def calculate_mape(actual: np.ndarray, pred: np.ndarray) -> float:
    """Calculate mean absolute percentage error."""
    mask = np.abs(actual) > 0.001
    if np.sum(mask) == 0:
        return float("nan")
    return np.mean(np.abs((actual[mask] - pred[mask]) / actual[mask])) * 100


class WeightedMSELoss(nn.Module):
    """Simple weighted MSE that penalises wrong direction predictions."""

    def __init__(self) -> None:
        super().__init__()
        self.mse = nn.MSELoss()

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        if pred.dim() == 3:
            pred = pred.squeeze(1)
        if target.dim() == 3:
            target = target.squeeze(1)
        mse_loss = self.mse(pred, target)
        direction_penalty = torch.mean(
            torch.abs(pred * target) * (torch.sign(pred) != torch.sign(target)).float()
        )
        return mse_loss + 0.1 * direction_penalty


class TimeXerOHLCPredictor:
    """Simplified wrapper around the `TimeXer` model for OHLC prediction."""

    def __init__(
        self,
        batch_size: int = 1000,
        db_config: dict | None = None,
        prediction_length: int = 1,
        context_length: int = 20,
    ) -> None:
        self.batch_size = batch_size
        self.prediction_length = prediction_length
        self.context_length = context_length
        self.models: dict[str, TimeXer] = {}
        self.db_config = db_config or {
            "host": "localhost",
            "port": 5432,
            "database": "your_database",
            "user": "your_username",
            "password": "your_password",
        }
        self.engine = create_engine(
            f"postgresql://{self.db_config['user']}:{self.db_config['password']}@"
            f"{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
        )

    def load_data_for_timexer(self, batch_idx: int = 0) -> pd.DataFrame:
        """Load a batch of OHLC data from PostgreSQL."""
        query = (
            "SELECT * FROM stock_daily_table ORDER BY symbol, date "
            f"LIMIT {self.batch_size} OFFSET {batch_idx * self.batch_size}"
        )
        try:
            return pd.read_sql_query(query, self.engine)
        except Exception as exc:
            print(f"데이터 로딩 실패: {exc}")
            return pd.DataFrame()

    def prepare_timeseries_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Basic preprocessing for TimeXer."""
        df = df.copy()
        df["time_idx"] = df.groupby("symbol").cumcount()
        df["group_id"] = df["symbol"].astype("category").cat.codes
        return df

    def create_timeseries_dataset(self, df: pd.DataFrame) -> TimeSeriesDataSet:
        target_cols = ["open", "high", "low", "close"]
        dataset = TimeSeriesDataSet(
            df,
            time_idx="time_idx",
            target=target_cols,
            group_ids=["group_id"],
            min_encoder_length=self.context_length,
            max_encoder_length=self.context_length,
            min_prediction_length=self.prediction_length,
            max_prediction_length=self.prediction_length,
            time_varying_unknown_reals=target_cols,
            static_categoricals=["symbol"],
            add_relative_time_idx=True,
        )
        return dataset

    def create_timexer_model(self, training_dataset: TimeSeriesDataSet) -> TimeXer:
        model = TimeXer.from_dataset(
            training_dataset,
            context_length=self.context_length,
            prediction_length=self.prediction_length,
            features="M",
            hidden_size=64,
            n_heads=4,
            e_layers=2,
            d_ff=256,
            dropout=0.1,
            patch_length=4,
            loss=WeightedMSELoss(),
        )
        return model

    def train(self, model: TimeXer, training_dataset: TimeSeriesDataSet) -> None:
        trainer = pl.Trainer(max_epochs=1, accelerator="cpu", logger=False)
        train_loader = training_dataset.to_dataloader(train=True, batch_size=32)
        trainer.fit(model, train_loader)


def main() -> None:
    predictor = TimeXerOHLCPredictor()
    df = predictor.load_data_for_timexer()
    if df.empty:
        print("No data available")
        return
    df_prepared = predictor.prepare_timeseries_data(df)
    dataset = predictor.create_timeseries_dataset(df_prepared)
    model = predictor.create_timexer_model(dataset)
    predictor.train(model, dataset)


if __name__ == "__main__":
    main()
