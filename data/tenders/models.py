from datetime import datetime, date
from typing import Optional

from sqlalchemy import Integer, func, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


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
    importedAt: Mapped[datetime] = mapped_column(default=func.now())
    tenderMetadata: Mapped["TenderMetadata"] = relationship(
        back_populates="master_tenders", cascade="all, delete-orphan"
    )


class TenderMetadata(Base):
    __tablename__ = "tender_metadata"
    id: Mapped[int] = mapped_column(ForeignKey("master_tenders.id"), primary_key=True)
    tender: Mapped["MasterTender"] = relationship(
        back_populates="tenderMetadata", single_parent=True
    )
    createdBy: Mapped[Optional[str]]
