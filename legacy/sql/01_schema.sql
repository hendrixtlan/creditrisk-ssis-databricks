-- Execute against a nonproduction SQL Server database.
IF OBJECT_ID('dbo.Payments','U') IS NOT NULL DROP TABLE dbo.Payments;
IF OBJECT_ID('dbo.Loans','U') IS NOT NULL DROP TABLE dbo.Loans;
IF OBJECT_ID('dbo.Customers','U') IS NOT NULL DROP TABLE dbo.Customers;
GO
CREATE TABLE dbo.Customers (
    customer_id BIGINT NOT NULL PRIMARY KEY,
    region NVARCHAR(40) NOT NULL,
    risk_band VARCHAR(10) NOT NULL,
    updated_at DATETIME2(3) NOT NULL
);
CREATE TABLE dbo.Loans (
    loan_id BIGINT NOT NULL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES dbo.Customers(customer_id),
    principal_amount DECIMAL(18,2) NOT NULL,
    outstanding_balance DECIMAL(18,2) NOT NULL,
    due_date DATE NOT NULL,
    updated_at DATETIME2(3) NOT NULL
);
CREATE TABLE dbo.Payments (
    payment_id BIGINT NOT NULL PRIMARY KEY,
    loan_id BIGINT NOT NULL REFERENCES dbo.Loans(loan_id),
    payment_amount DECIMAL(18,2) NOT NULL,
    payment_date DATE NOT NULL,
    updated_at DATETIME2(3) NOT NULL
);
CREATE INDEX IX_Customers_Updated ON dbo.Customers(updated_at);
CREATE INDEX IX_Loans_Updated ON dbo.Loans(updated_at);
CREATE INDEX IX_Payments_Updated ON dbo.Payments(updated_at);
GO
