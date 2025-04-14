from datetime import datetime, date
from typing import Optional

from sqlalchemy import Integer, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class NewTender(Base):
    __tablename__ = "new_tenders"

    id = mapped_column(Integer, primary_key=True)
    tenderId: Mapped[str]
    title: Mapped[Optional[str]]
    solicitationType: Mapped[Optional[str]]
    procurementEntity: Mapped[Optional[str]]
    endUserEntity: Mapped[Optional[str]]
    closingDate: Mapped[Optional[datetime]]
    postDate: Mapped[Optional[date]]
    tenderStatus: Mapped[Optional[str]]


class MasterTender(Base):
    __tablename__ = "master_tenders"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenderId: Mapped[str]
    title: Mapped[Optional[str]]
    solicitationType: Mapped[Optional[str]]
    procurementEntity: Mapped[Optional[str]]
    endUserEntity: Mapped[Optional[str]]
    closingDate: Mapped[Optional[datetime]]
    postDate: Mapped[Optional[date]]
    tenderStatus: Mapped[Optional[str]]
    imported_at: Mapped[datetime] = mapped_column(default=func.now())
