import asyncio
from auth.database import SessionLocal
from auth.blocklist_cache import blocked_ips, blocked_domains
from users.models import BlocklistEntry


async def refresh_blocklist_periodically(interval: int = 60):
    while True:
        try:
            db = SessionLocal()
            entries = db.query(BlocklistEntry).all()

            # Clear old sets
            blocked_ips.clear()
            blocked_domains.clear()

            for entry in entries:
                if entry.type == "ip" and entry.value:
                    blocked_ips.add(entry.value)
                elif entry.type == "domain" and entry.value:
                    blocked_domains.add(entry.value)

            print("✅ Blocklist refreshed")
        except Exception as e:
            print("❌ Error refreshing blocklist:", e)
        finally:
            db.close()

        await asyncio.sleep(interval)
