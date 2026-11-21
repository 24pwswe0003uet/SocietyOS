"""Seed the database with Pakistani universities for development."""

import asyncio
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.university import University

UNIVERSITIES = [
    {"name": "University of Engineering and Technology (UET) Lahore", "city": "Lahore"},
    {"name": "LUMS - Lahore University of Management Sciences", "city": "Lahore"},
    {"name": "NUST - National University of Sciences and Technology", "city": "Islamabad"},
    {"name": "FAST-NUCES", "city": "Islamabad"},
    {"name": "COMSATS University Islamabad", "city": "Islamabad"},
    {"name": "IBA Karachi", "city": "Karachi"},
    {"name": "NED University of Engineering and Technology", "city": "Karachi"},
    {"name": "University of the Punjab", "city": "Lahore"},
    {"name": "Quaid-i-Azam University", "city": "Islamabad"},
    {"name": "PIEAS", "city": "Islamabad"},
]


async def seed_universities():
    """Insert universities if the table is empty."""
    async with async_session_factory() as session:
        result = await session.execute(select(University).limit(1))
        if result.scalar_one_or_none():
            print("Universities already seeded.")
            return

        for uni in UNIVERSITIES:
            session.add(University(name=uni["name"], city=uni["city"], country="Pakistan"))

        await session.commit()
        print(f"Seeded {len(UNIVERSITIES)} universities.")


if __name__ == "__main__":
    asyncio.run(seed_universities())
