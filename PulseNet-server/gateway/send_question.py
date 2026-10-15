import asyncio
from bleak import BleakClient


# =====================================================
# DEVICE
# =====================================================

DEVICE_ADDRESS = "54:43:B2:DC:B0:B2"


# =====================================================
# BLE UUID
# =====================================================

REGISTRATION_CHAR_UUID = \
    "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"

QUESTION_CHAR_UUID = \
    "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

ANSWER_CHAR_UUID = \
    "6E400004-B5A3-F393-E0A9-E50E24DCCA9E"

ACK_CHAR_UUID = \
    "6E400005-B5A3-F393-E0A9-E50E24DCCA9E"


# =====================================================
# CALLBACK - REGISTRATION
# ESP32 -> Raspberry Pi
# =====================================================

def registration_callback(characteristic, data):
    message = data.decode("utf-8", errors="replace")

    print("\n")
    print("======================================")
    print("[REGISTRATION RECEIVED]")
    print("======================================")
    print(message)
    print("======================================")


# =====================================================
# CALLBACK - ANSWER
# ESP32 -> Raspberry Pi
# =====================================================

def answer_callback(characteristic, data):
    message = data.decode("utf-8", errors="replace")

    print("\n")
    print("======================================")
    print("[ANSWER RECEIVED]")
    print("======================================")
    print(message)
    print("======================================")


# =====================================================
# SEND ACK
# Raspberry Pi -> ESP32
# =====================================================

async def send_ack(client, message=None):

    if message is None:
        message = '{"type":"ACK","status":"CONNECTED"}'

    data = message.encode("utf-8")

    print("\n======================================")
    print("[ACK TX]")
    print("======================================")
    print(message)

    await client.write_gatt_char(
        ACK_CHAR_UUID,
        data,
        response=True
    )

    print("[OK] ACK sent")
    print("======================================")


# =====================================================
# SEND QUESTION
# Raspberry Pi -> ESP32
# =====================================================

async def send_question(client, question):

    if not question:
        print("[ERROR] Question is empty.")
        return

    data = question.encode("utf-8")

    print("\n======================================")
    print("[QUESTION TX]")
    print("======================================")
    print(f"Question: {question}")
    print(f"Bytes   : {len(data)}")

    try:

        await client.write_gatt_char(
            QUESTION_CHAR_UUID,
            data,
            response=True
        )

        print("[OK] Question sent successfully.")

    except Exception as e:

        print("[ERROR] Failed to send question.")
        print(f"Reason: {type(e).__name__}: {e}")

    print("======================================")


# =====================================================
# SEND TEST QUESTION
# =====================================================

async def send_test_question(client):

    question = "Which protocol is low power?"

    await send_question(
        client,
        question
    )


# =====================================================
# SHOW MENU
# =====================================================

def show_menu():

    print("\n")
    print("======================================")
    print("          PulseNet BLE Gateway")
    print("======================================")
    print("1. Send test question")
    print("2. Send custom question")
    print("3. Send ACK")
    print("4. Show BLE connection status")
    print("5. Exit")
    print("======================================")


# =====================================================
# MENU LOOP
# =====================================================

async def menu_loop(client):

    while True:

        show_menu()

        choice = await asyncio.to_thread(
            input,
            "Select option: "
        )

        choice = choice.strip()

        # ---------------------------------------------
        # OPTION 1
        # Send test question
        # ---------------------------------------------

        if choice == "1":

            await send_test_question(client)

        # ---------------------------------------------
        # OPTION 2
        # Send custom question
        # ---------------------------------------------

        elif choice == "2":

            question = await asyncio.to_thread(
                input,
                "Enter question: "
            )

            question = question.strip()

            if question:

                await send_question(
                    client,
                    question
                )

            else:

                print("[ERROR] Question cannot be empty.")

        # ---------------------------------------------
        # OPTION 3
        # Send ACK
        # ---------------------------------------------

        elif choice == "3":

            ack = '{"type":"ACK","status":"OK"}'

            await send_ack(
                client,
                ack
            )

        # ---------------------------------------------
        # OPTION 4
        # Connection status
        # ---------------------------------------------

        elif choice == "4":

            if client.is_connected:

                print("\n[STATUS] BLE connected.")

            else:

                print("\n[STATUS] BLE disconnected.")

        # ---------------------------------------------
        # OPTION 5
        # Exit
        # ---------------------------------------------

        elif choice == "5":

            print("\n[INFO] Exiting gateway...")
            break

        else:

            print("\n[ERROR] Invalid option.")

        await asyncio.sleep(0.2)


# =====================================================
# MAIN
# =====================================================

async def main():

    print("======================================")
    print("       PulseNet BLE Gateway")
    print("======================================")
    print(f"Target device: {DEVICE_ADDRESS}")
    print()

    try:

        # -------------------------------------------------
        # CONNECT
        # -------------------------------------------------

        async with BleakClient(DEVICE_ADDRESS) as client:

            print("[OK] BLE connected")

            # -------------------------------------------------
            # SHOW GATT SERVICES
            # -------------------------------------------------

            print("\n[INFO] GATT services:")

            for service in client.services:

                print(f"\nService: {service.uuid}")

                for char in service.characteristics:

                    print(
                        f"  Characteristic: {char.uuid} "
                        f"properties={char.properties}"
                    )

            # -------------------------------------------------
            # SUBSCRIBE REGISTRATION
            # -------------------------------------------------

            print("\n[INFO] Subscribing to registration notifications...")

            await client.start_notify(
                REGISTRATION_CHAR_UUID,
                registration_callback
            )

            # -------------------------------------------------
            # SUBSCRIBE ANSWER
            # -------------------------------------------------

            print("[INFO] Subscribing to answer notifications...")

            await client.start_notify(
                ANSWER_CHAR_UUID,
                answer_callback
            )

            print("[OK] Notification handlers enabled")

            # -------------------------------------------------
            # SEND INITIAL ACK
            # -------------------------------------------------

            ack = '{"type":"ACK","status":"CONNECTED"}'

            await send_ack(
                client,
                ack
            )

            # -------------------------------------------------
            # START MENU
            # -------------------------------------------------

            print("\n======================================")
            print(" Gateway is running")
            print("======================================")

            await menu_loop(client)

            # -------------------------------------------------
            # CLEANUP
            # -------------------------------------------------

            try:

                await client.stop_notify(
                    REGISTRATION_CHAR_UUID
                )

                await client.stop_notify(
                    ANSWER_CHAR_UUID
                )

            except Exception:
                pass

            print("\n[INFO] BLE notifications stopped.")

    except Exception as e:

        print("\n======================================")
        print("[ERROR] BLE Gateway failed")
        print("======================================")
        print(f"Type   : {type(e).__name__}")
        print(f"Reason : {e}")
        print("======================================")


# =====================================================
# PROGRAM ENTRY
# =====================================================

if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        print("\n")
        print("======================================")
        print("[INFO] Gateway stopped by user.")
        print("======================================")
