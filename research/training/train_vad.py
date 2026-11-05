"""Train CNN-LSTM baseline for Video Anomaly Detection.

Usage:
    python -m research.training.train_vad --config configs/research_config.yaml --epochs 50
    python -m research.training.train_vad --epochs 1 --batch-size 4  # smoke test
"""

import argparse
import logging
import os
import time

import yaml
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from research.training.trainer_utils import (
    set_seed, EarlyStopping, MetricTracker,
    ExperimentMetadata, save_experiment_metadata,
)

logger = logging.getLogger(__name__)


def create_model(config: dict, device: str) -> nn.Module:
    """Create CNN-LSTM model from config."""
    from research.models.cnn_lstm import CNNLSTM
    model = CNNLSTM(
        backbone_name=config.get("backbone", "resnet18"),
        pretrained=config.get("pretrained", True),
        embedding_dim=config.get("embedding_dim", 512),
        lstm_hidden=config.get("lstm_hidden", 256),
        lstm_layers=config.get("lstm_layers", 2),
        dropout=config.get("dropout", 0.3),
    )
    return model.to(device)


def train_epoch(model, dataloader, criterion, optimizer, device):
    """Run one training epoch. Returns avg loss."""
    model.train()
    total_loss = 0.0
    count = 0
    for batch in dataloader:
        frames, labels = batch[0].to(device), batch[1].float().to(device)
        optimizer.zero_grad()
        output = model(frames)
        loss = criterion(output["anomaly_score"], labels)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * labels.size(0)
        count += labels.size(0)
    return total_loss / max(count, 1)


def validate_epoch(model, dataloader, criterion, device):
    """Run validation. Returns avg loss and predictions."""
    model.eval()
    total_loss = 0.0
    count = 0
    all_preds, all_labels = [], []
    with torch.no_grad():
        for batch in dataloader:
            frames, labels = batch[0].to(device), batch[1].float().to(device)
            output = model(frames)
            loss = criterion(output["anomaly_score"], labels)
            total_loss += loss.item() * labels.size(0)
            count += labels.size(0)
            all_preds.extend(output["anomaly_score"].cpu().tolist())
            all_labels.extend(labels.cpu().tolist())
    return total_loss / max(count, 1), all_preds, all_labels


def main():
    parser = argparse.ArgumentParser(description="Train CNN-LSTM VAD baseline")
    parser.add_argument("--config", default="configs/research_config.yaml")
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--lr", type=float, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", default="results/vad/cnn_lstm")
    parser.add_argument("--resume", default=None, help="Checkpoint path to resume")
    parser.add_argument("--backbone", default=None)
    parser.add_argument("--data-dir", default="data/vad")
    args = parser.parse_args()

    # Load config
    config = {}
    if os.path.exists(args.config):
        with open(args.config) as f:
            config = yaml.safe_load(f) or {}

    model_cfg = config.get("cnn_lstm", {})
    train_cfg = config.get("training", {})
    data_cfg = config.get("data", {})

    # CLI overrides
    epochs = args.epochs or train_cfg.get("epochs", 50)
    batch_size = args.batch_size or train_cfg.get("batch_size", 8)
    lr = args.lr or train_cfg.get("learning_rate", 0.001)
    if args.backbone:
        model_cfg["backbone"] = args.backbone

    # Setup
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    set_seed(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    os.makedirs(args.output_dir, exist_ok=True)

    logger.info(f"Training CNN-LSTM: epochs={epochs}, batch={batch_size}, lr={lr}, device={device}")

    # Create model
    model = create_model(model_cfg, device)
    info = model.get_model_info()
    logger.info(f"Model: {info['total_parameters']:,} params ({info['trainable_parameters']:,} trainable)")

    # Freeze backbone initially if configured
    freeze_epochs = model_cfg.get("freeze_backbone_epochs", 0)
    if freeze_epochs > 0:
        model.freeze_backbone()
        logger.info(f"Backbone frozen for first {freeze_epochs} epochs")

    # Dataset
    try:
        from research.datasets.vad_dataset import VADDataset
        train_dataset = VADDataset.from_directory(args.data_dir, split="train", **data_cfg)
        val_dataset = VADDataset.from_directory(args.data_dir, split="val", **data_cfg)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True,
                                  num_workers=train_cfg.get("num_workers", 0))
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False,
                                num_workers=train_cfg.get("num_workers", 0))
    except Exception as e:
        logger.error(f"Dataset loading failed: {e}")
        logger.info("To train, prepare data in data/vad/ directory. See data/vad/README.md")
        return

    # Training setup
    criterion = nn.BCELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr,
                                 weight_decay=train_cfg.get("weight_decay", 1e-4))
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min",
        patience=train_cfg.get("scheduler_patience", 5),
        factor=train_cfg.get("scheduler_factor", 0.5),
    )
    early_stopping = EarlyStopping(
        patience=train_cfg.get("early_stopping_patience", 10), mode="min",
    )
    tracker = MetricTracker()

    # Resume
    start_epoch = 0
    if args.resume and os.path.exists(args.resume):
        ckpt = torch.load(args.resume, map_location=device)
        model.load_state_dict(ckpt["model_state_dict"])
        optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        start_epoch = ckpt.get("epoch", 0)
        logger.info(f"Resumed from epoch {start_epoch}")

    # Metadata
    metadata = ExperimentMetadata(
        experiment_id=f"cnn_lstm_{args.seed}_{int(time.time())}",
        model="CNN-LSTM", dataset=args.data_dir, device=device, seed=args.seed,
        config_snapshot={"model": model_cfg, "training": train_cfg, "data": data_cfg},
    )

    # Training loop
    best_val_loss = float("inf")
    for epoch in range(start_epoch, epochs):
        # Unfreeze backbone after freeze_epochs
        if freeze_epochs > 0 and epoch == freeze_epochs:
            model.unfreeze_backbone()

        train_loss = train_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_preds, val_labels = validate_epoch(model, val_loader, criterion, device)
        scheduler.step(val_loss)

        tracker.update({"train_loss": train_loss, "val_loss": val_loss,
                        "lr": optimizer.param_groups[0]["lr"]})
        logger.info(f"Epoch {epoch+1}/{epochs} — train_loss: {train_loss:.4f}, val_loss: {val_loss:.4f}")

        # Save best
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save({
                "epoch": epoch + 1, "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_loss": val_loss,
            }, os.path.join(args.output_dir, "best_model.pt"))

        if early_stopping(val_loss):
            logger.info(f"Early stopping at epoch {epoch+1}")
            break

    # Save final
    torch.save({"epoch": epochs, "model_state_dict": model.state_dict()},
               os.path.join(args.output_dir, "last_model.pt"))
    tracker.save_to_csv(os.path.join(args.output_dir, "training_metrics.csv"))
    save_experiment_metadata(metadata, os.path.join(args.output_dir, "metadata.json"))
    logger.info(f"Training complete. Best val_loss: {best_val_loss:.4f}")


if __name__ == "__main__":
    main()
