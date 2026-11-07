"""Import the Fase I CSV export into the contract-based store.

Usage::

    python manage.py import_fase1_export
    python manage.py import_fase1_export --dir /path/to/data_export/csv
    python manage.py import_fase1_export --profile /tmp/perfil.json

What it does (monograph OE1 / RF-01 / CP-08):

1. reads the versioned export with ``Fase1ExportAdapter`` (pure Python),
2. maps it to minimum-contract payloads (Tabla 8) + quality profile,
3. ingests them through ``IngestSessionContract`` (duplicates skipped),
4. writes the data-quality profile as JSON so the profiling evidence is
   reproducible (RNF-09).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.athletes.infrastructure.repositories import DjangoAthleteRepository
from apps.sessions.application import IngestSessionContract
from apps.sessions.infrastructure.contract_validator import JsonContractValidator
from apps.sessions.infrastructure.file_ingest import Fase1ExportAdapter
from apps.sessions.infrastructure.repositories import DjangoSessionRepository

DEFAULT_CSV_DIR = Path(settings.BASE_DIR).parent / "data_export" / "csv"
DEFAULT_PROFILE = Path(settings.BASE_DIR).parent / "data_export" / "perfil_calidad_fase1.json"


class Command(BaseCommand):
    help = (
        "Importa la exportación CSV de la Fase I al contrato mínimo de datos "
        "y escribe el perfil de calidad (JSON)."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--dir",
            default=str(DEFAULT_CSV_DIR),
            help="Directorio con los CSV exportados de la Fase I.",
        )
        parser.add_argument(
            "--profile",
            default=str(DEFAULT_PROFILE),
            help="Ruta de salida del perfil de calidad en JSON.",
        )

    def handle(self, *args, **options) -> None:
        csv_dir = Path(options["dir"])
        if not csv_dir.exists():
            raise CommandError("No existe el directorio: {0}".format(csv_dir))

        batch = Fase1ExportAdapter(csv_dir).load()
        session_repository = DjangoSessionRepository()

        pending, already = [], 0
        for payload in batch.payloads:
            if session_repository.exists(payload["session_id"]):
                already += 1
            else:
                pending.append(payload)

        result = IngestSessionContract(
            session_repository,
            DjangoAthleteRepository(),
            JsonContractValidator(),
        ).execute(pending) if pending else None

        profile = dict(batch.profile)
        profile["generated_at"] = datetime.now(timezone.utc).isoformat()
        profile["ingestion"] = {
            "already_ingested": already,
            "accepted": result.accepted if result else 0,
            "rejected": result.rejected if result else 0,
            "errors": [
                {
                    "session_id": error.session_id,
                    "field": error.field,
                    "message": error.message,
                }
                for error in (result.errors if result else ())
            ],
        }

        profile_path = Path(options["profile"])
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(
            json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Sesiones aceptadas: {0} | rechazadas: {1} | ya ingeridas: {2}".format(
                    profile["ingestion"]["accepted"],
                    profile["ingestion"]["rejected"],
                    already,
                )
            )
        )
        self.stdout.write("Perfil de calidad: {0}".format(profile_path))
