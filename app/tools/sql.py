import logging
from sqlalchemy import Column, String, Float, Integer, MetaData, Table, inspect, text
from app.db import engine, SessionLocal, Base
from langchain_core.tools import tool

logger = logging.getLogger("research_engine.tools.sql")

# Define Mock Tables
class CompanyFinancials(Base):
    __tablename__ = "company_financials"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), unique=True, nullable=False)
    company_name = Column(String(100), nullable=False)
    revenue = Column(Float, nullable=False)  # in billions
    net_income = Column(Float, nullable=False)  # in billions
    pe_ratio = Column(Float, nullable=True)
    fiscal_year = Column(Integer, nullable=False)

class MarketMetrics(Base):
    __tablename__ = "market_metrics"
    id = Column(Integer, primary_key=True, autoincrement=True)
    sector = Column(String(50), unique=True, nullable=False)
    market_size = Column(Float, nullable=False)  # in billions
    growth_rate = Column(Float, nullable=False)  # CAGR percentage
    top_competitors = Column(String(200), nullable=False)

# Seed Mock Data function
def seed_mock_database():
    """Create tables and seed mock data if database is empty."""
    try:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        
        # Check if table has records
        if db.query(CompanyFinancials).count() == 0:
            logger.info("Seeding mock company financials data...")
            financials = [
                CompanyFinancials(ticker="AAPL", company_name="Apple Inc.", revenue=385.7, net_income=97.0, pe_ratio=31.2, fiscal_year=2023),
                CompanyFinancials(ticker="MSFT", company_name="Microsoft Corp.", revenue=211.9, net_income=72.4, pe_ratio=35.8, fiscal_year=2023),
                CompanyFinancials(ticker="GOOGL", company_name="Alphabet Inc.", revenue=307.4, net_income=73.8, pe_ratio=26.4, fiscal_year=2023),
                CompanyFinancials(ticker="AMZN", company_name="Amazon.com Inc.", revenue=574.8, net_income=30.4, pe_ratio=62.5, fiscal_year=2023),
                CompanyFinancials(ticker="TSLA", company_name="Tesla Inc.", revenue=96.8, net_income=15.0, pe_ratio=45.1, fiscal_year=2023),
            ]
            db.add_all(financials)
            
        if db.query(MarketMetrics).count() == 0:
            logger.info("Seeding mock market metrics data...")
            metrics = [
                MarketMetrics(sector="Consumer Electronics", market_size=1200.0, growth_rate=5.2, top_competitors="Apple, Samsung, Sony, Xiaomi"),
                MarketMetrics(sector="Cloud Computing", market_size=670.0, growth_rate=16.4, top_competitors="Microsoft Azure, AWS, Google Cloud"),
                MarketMetrics(sector="Electric Vehicles", market_size=380.0, growth_rate=22.8, top_competitors="Tesla, BYD, Volkswagen, NIO"),
                MarketMetrics(sector="Generative AI", market_size=40.0, growth_rate=42.0, top_competitors="OpenAI, Anthropic, Google, Meta"),
            ]
            db.add_all(metrics)
            
        db.commit()
        db.close()
        logger.info("Mock database tables seeded successfully.")
    except Exception as e:
        logger.error(f"Failed to seed mock database: {e}")

# Tool definition
@tool
def query_mock_database(sql_query: str) -> str:
    """
    Execute SQL read queries against the mock enterprise database.
    Available Tables:
    - company_financials (columns: id, ticker, company_name, revenue, net_income, pe_ratio, fiscal_year)
    - market_metrics (columns: id, sector, market_size, growth_rate, top_competitors)
    Use this to retrieve validated corporate financials and market stats.
    """
    logger.info(f"Executing SQL query: {sql_query}")
    db = SessionLocal()
    try:
        # Prevent write operations
        query_lower = sql_query.lower().strip()
        if any(keyword in query_lower for keyword in ["insert", "update", "delete", "drop", "truncate", "create", "alter"]):
            return "Error: Only SELECT queries are permitted on the enterprise database."
            
        result = db.execute(text(sql_query))
        rows = result.fetchall()
        column_names = result.keys()
        
        if not rows:
            return "Query returned 0 results."
            
        # Format results as text
        output = [", ".join(column_names)]
        for row in rows:
            output.append(", ".join(str(val) for val in row))
            
        return "\n".join(output)
    except Exception as e:
        logger.error(f"SQL execution failed: {e}")
        return f"SQL Query Error: {str(e)}"
    finally:
        db.close()
