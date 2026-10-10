import os
import subprocess
import sys
import time

from scripts.backfill_user_names import backfill
from scripts.run_contract import run_contract
from scripts.set_migration_phase import set_phase
from scripts.verify_backfill import verify_backfill


def main() -> None:
    print("=" * 64)
    print("       CP2 ZERO-DOWNTIME MIGRATION - FULL REHEARSAL DEMO        ")
    print("=" * 64)

    # 1. Start traffic generator in background
    duration = 35.0  # seconds
    print(f"\n[STEP 0] Launching traffic generator in background (duration: {duration}s)...")
    traffic_proc = subprocess.Popen(
        [sys.executable, "-m", "scripts.traffic_gen", "--duration", str(duration), "--rate", "25"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        # Give traffic generator 3 seconds to ramp up
        time.sleep(3.0)

        # 2. Phase 1: Expand
        print("\n" + "-" * 64)
        print("[PHASE 1: EXPAND] Setting active phase to 'expand'...")
        set_phase("expand")
        time.sleep(2.0)

        # 3. Phase 2: Dual-Write
        print("\n" + "-" * 64)
        print("[PHASE 2: DUAL-WRITE] Setting active phase to 'dual_write'...")
        set_phase("dual_write")
        time.sleep(3.0)

        # 4. Phase 3: Backfill
        print("\n" + "-" * 64)
        print("[PHASE 3: BACKFILL] Starting batched keyset backfill...")
        set_phase("backfill")
        backfill()
        print("\n[VERIFICATION] Verifying data consistency after backfill...")
        verify_backfill()
        time.sleep(2.0)

        # 5. Phase 4: Switch-Read
        print("\n" + "-" * 64)
        print("[PHASE 4: SWITCH-READ] Setting active phase to 'switch_read'...")
        set_phase("switch_read")
        time.sleep(3.0)

        # 6. Phase 5: Contract
        print("\n" + "-" * 64)
        print("[PHASE 5: CONTRACT] Executing contract migration...")
        run_contract()
        time.sleep(4.0)

        print("\n" + "-" * 64)
        print("[WAIT] Waiting for traffic generator to complete remaining cycles...")
        stdout, _ = traffic_proc.communicate()
        print(stdout)

        if traffic_proc.returncode != 0:
            print("[FAIL] Traffic generator detected errors or SLA violations!", file=sys.stderr)
            sys.exit(1)

        print("\n[VERIFICATION] Final verification queries...")
        if not verify_backfill():
            print("[FAIL] Final verification failed!", file=sys.stderr)
            sys.exit(1)

        print("\n" + "=" * 64)
        print(" [SUCCESS] CP2 ZERO-DOWNTIME MIGRATION COMPLETED SUCCESSFULLY! ")
        print("   - 5 Phases Executed Smoothly")
        print("   - Continuous Traffic Maintained (>= 20 req/s)")
        print("   - Zero HTTP 5xx Server Errors")
        print("   - p99 Latency Well Under 500ms")
        print("   - 100% Data Integrity Preserved")
        print("=" * 64)

    except Exception as error:
        traffic_proc.terminate()
        print(f"\n[FATAL ERROR] Demo aborted: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
