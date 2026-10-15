import asyncio
from bleak import BleakClient

DEVICE_ADDRESS = "54:43:B2:DC:B0:B2"

REGISTRATION_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
QUESTION_CHAR_UUID     = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
ANSWER_CHAR_UUID       = "6E400004-B5A3-F393-E0A9-E50E24DCCA9E"
ACK_CHAR_UUID          = "6E400005-B5A3-F393-E0A9-E50E24DCCA9E"


def registration_callback(characteristic, data):
    message = data.decode("utf-8", errors="replace")
    print("\n[REGISTRATION]")
    print(message)


def answer_callback(characteristic, data):
    message = data.decode("utf-8", errors="replace")
    print("\n[ANSWER]")
    print(message)


async def main():

    print("======================================")
    print(" PulseNet BLE Gateway")
    print("======================================")
    print(f"Target: {DEVICE_ADDRESS}")
    print()

    async with BleakClient(DEVICE_ADDRESS) as client:

        print("[OK] BLE connected")

        print("\n[INFO] GATT services:")

        for service in client.services:
            print(f"\nService: {service.uuid}")

            for char in service.characteristics:
                print(
                    f"  Characteristic: {char.uuid} "
                    f"properties={char.properties}"
                )

        print("\n[INFO] Subscribing to notifications...")

        await client.start_notify(
            REGISTRATION_CHAR_UUID,
            registration_callback
        )

        await client.start_notify(
            ANSWER_CHAR_UUID,
            answer_callback
        )

        print("[OK] Notification handlers enabled")

        # Send test ACK to student device
        ack = b'{"type":"ACK","status":"CONNECTED"}'

        await client.write_gatt_char(
            ACK_CHAR_UUID,
            ack,
            response=True
        )

        print("[OK] ACK sent")

        print("\n======================================")
        print(" Gateway is running")
        print(" Press Ctrl+C to stop")
        print("======================================")

        while True:
            await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\n[INFO] Gateway stopped")

    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
