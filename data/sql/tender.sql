CREATE TABLE master_tenders (
  id INTEGER PRIMARY KEY,
  tenderId TEXT NOT NULL,
  title TEXT,
  solicitationType TEXT,
  procurementEntity TEXT,
  endUserEntity TEXT,
  closingDate TIMESTAMP,
  postDate DATE,
  tenderStatus TEXT,
  importedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tender_metadata (
  id INTEGER PRIMARY KEY,
  createdBy TEXT,
  FOREIGN KEY (id) REFERENCES master_tenders (id) ON DELETE CASCADE
);
