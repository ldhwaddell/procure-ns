from datetime import datetime, date
from typing import Optional

from sqlalchemy.dialects.postgresql import JSONB
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
        back_populates="tender", cascade="all, delete-orphan"
    )


class TenderMetadata(Base):
    __tablename__ = "tender_metadata"
    id: Mapped[int] = mapped_column(ForeignKey("master_tenders.id"), primary_key=True)
    tender: Mapped["MasterTender"] = relationship(
        back_populates="tenderMetadata", single_parent=True
    )
    tenderId: Mapped[Optional[str]]
    solicitationType: Mapped[Optional[str]]
    title: Mapped[Optional[str]]
    procurementMethod: Mapped[Optional[str]]
    createdBy: Mapped[Optional[str]]
    modifiedBy: Mapped[Optional[str]]
    createdDate: Mapped[Optional[datetime]]
    modifiedDate: Mapped[Optional[datetime]]
    contactName: Mapped[Optional[str]]
    contactEmail: Mapped[Optional[str]]
    contactPhoneNumber: Mapped[Optional[str]]
    contactProvince: Mapped[Optional[str]]
    contactDetails: Mapped[Optional[str]]
    procurementEntity: Mapped[Optional[str]]
    endUserEntity: Mapped[Optional[str]]
    endUserEntityOrganizationId: Mapped[Optional[str]]
    tenderUrl: Mapped[Optional[str]]
    closingDate: Mapped[Optional[str]]
    closingTime: Mapped[Optional[str]]
    closingDateDisplay: Mapped[Optional[str]]
    description: Mapped[Optional[str]]
    memo: Mapped[Optional[str]]
    issuedDate: Mapped[Optional[str]]
    tenderStatus: Mapped[Optional[str]]
    expectedDurationOfContract: Mapped[Optional[int]]
    pickUpFee: Mapped[Optional[str]]
    termsOfPayment: Mapped[Optional[str]]
    sustainablePrimaryReason: Mapped[Optional[str]]
    sustainablePrimarySource: Mapped[Optional[str]]
    closingLocation: Mapped[Optional[str]]
    closingLocationOtherText: Mapped[Optional[str]]
    publicOpeningDate: Mapped[Optional[str]]
    publicOpeningTime: Mapped[Optional[str]]
    publicOpeningLocation: Mapped[Optional[str]]
    submissionLanguage: Mapped[Optional[str]]
    awardMemo: Mapped[Optional[str]]
    postDate: Mapped[Optional[str]]

    # Complex/Nested fields as JSONB
    contactMethod: Mapped[Optional[dict]] = mapped_column(JSONB)
    tradeAgreement: Mapped[Optional[dict]] = mapped_column(JSONB)
    attachments: Mapped[Optional[dict]] = mapped_column(JSONB)
    tenderAwardData: Mapped[Optional[dict]] = mapped_column(JSONB)
    tenderBidInformationDataList: Mapped[Optional[dict]] = mapped_column(JSONB)
    unspscLevelData: Mapped[Optional[dict]] = mapped_column(JSONB)
    procumentEntityData: Mapped[Optional[dict]] = mapped_column(JSONB)
    procurementContactInformation: Mapped[Optional[dict]] = mapped_column(JSONB)
    procurementContactMethod: Mapped[Optional[dict]] = mapped_column(JSONB)
    informationInDocument: Mapped[Optional[dict]] = mapped_column(JSONB)
    relevantRegions: Mapped[Optional[dict]] = mapped_column(JSONB)
