# Hướng dẫn chạy PulseNet (trang giáo viên) trên Raspberry Pi

## 1. Chuẩn bị (kiểm tra 30 giây)

- Raspberry Pi đã bật điện và nối cùng mạng Wi-Fi với máy tính / điện thoại.
- Địa chỉ Pi hiện tại: **192.168.50.2**
- Backend không tự chạy sau khi Pi bật lại → mỗi lần bật lại Pi chỉ cần làm **Bước 2** (10 giây).

## 2. Khởi động backend (làm sau mỗi lần bật lại Pi)

Mở terminal trên máy tính (PowerShell hoặc Git Bash), gõ:

```
ssh katespi@192.168.50.2
```

(Máy này đã được cài key nên vào thẳng không cần mật khẩu.)

Trên Pi gõ tiếp:

```
cd ~/pulsenet
./start_server.sh
./start_gateway.sh
```

Nếu thấy dòng `[OK] Backend da KHOI DONG thanh cong` và `[OK] Gateway da KHOI DONG` là xong. Mở trang web kiểm tra badge "Gateway: ĐÃ NỐI THIẾT BỊ" màu xanh (thiết bị ESP32 phải đang bật).

## 3. Mở trang giáo viên

Mở trình duyệt (máy tính hoặc điện thoại chung mạng Wi-Fi) vào:

**http://192.168.50.2:8000/**

Góc trên phải có badge màu xanh **"Đã kết nối server"** là web chạy tốt.

## 4. Các lệnh thường dùng (gõ trên Pi, đứng trong `~/pulsenet`)

| Lệnh | Tác dụng |
|---|---|
| `./status_server.sh` | Kiểm tra backend đang chạy hay không |
| `./start_server.sh` | Khởi động backend (nếu đang chạy rồi thì chỉ báo, không chạy doubled) |
| `./stop_server.sh` | Dừng backend |
| `tail -f backend/uvicorn.log` | Xem log chạy trực tiếp (Ctrl+C để thoát xem) |

Thoát khỏi SSH về máy tính: gõ `exit`.

## 5. Luồng dùng cơ bản trên trang web

1. Gõ tên quiz vào ô trống → bấm **+ Tạo quiz**.
2. Tab **Câu hỏi**: bấm **⬇ Tải mẫu CSV**, soạn câu hỏi theo mẫu, chọn file → **⬆ Nhập câu hỏi**. Sau đó đặt **⏱ Thời gian làm bài** (phút) — đây là đồng hồ đếm ngược cho **cả bài quiz** hiển thị trên thiết bị.
3. Tab **Điều khiển & Giám sát**: chờ sinh viên đăng ký trên thiết bị → bấm **▶ Bắt đầu quiz**. Đồng hồ bắt đầu chạy.
4. Từ đó mọi thứ **tự động**: câu hỏi tự chuyển trên thiết bị sau mỗi lượt trả lời (đáp án được tô xanh khi chọn); hết giờ bài quiz **tự kết thúc** và thiết bị hiện kết quả: số câu đúng / tổng câu + điểm /10 (câu không kịp trả lời tính là sai).
5. Suốt buổi học, bảng **"Theo dõi sinh viên trực tiếp"** cho biết từng sinh viên đang làm câu mấy, đã trả lời bao nhiêu, đúng/sai và điểm — cập nhật mỗi 2 giây. Không còn nút "Câu tiếp theo".

> Lưu ý: câu hỏi trên màn hình thiết bị hiển thị tốt nhất với tiếng Việt **không dấu** (font màn hình chỉ hỗ trợ ASCII). Giao diện trên thiết bị hiển thị tiếng Anh.

## 8. Nạp firmware mới cho thiết bị ESP32 (chỉ khi code thiết bị thay đổi)

Firmware đã build sẵn tại:
`D:\UTE\IOT\PULSE_NET\PulseNet-device\.pio\build\esp32dev\firmware.bin`

Cách nạp (một trong hai):
- **VSCode + PlatformIO**: mở thư mục `PulseNet-device` → PlatformIO → Upload (cắm ESP32 qua USB).
- **Terminal**: `cd D:\UTE\IOT\PULSE_NET\PulseNet-device && py -3 -m platformio run -e esp32dev -t upload`.

Sau khi nạp: thiết bị tự chạy lại, gateway tự kết nối lại trong vài giây (xem badge trên web).

## 6. Nếu mở web không được

1. Trên Pi chạy `./status_server.sh` — nếu `[DUNG]` thì chạy `./start_server.sh`.
2. Nếu vẫn lỗi: `tail -20 backend/uvicorn.log` để xem lỗi cụ thể.
3. Nếu router đổi IP của Pi: trên Pi gõ `hostname -I` để lấy IP mới, rồi dùng IP đó trong trình duyệt.

## 7. Gateway BLE (bắt buộc khi dùng thiết bị ESP32)

Gateway là cầu nối BLE giữa Pi và thiết bị sinh viên. **Không chạy gateway = thiết bị không kết nối được.**

Cập nhật mới: gateway chạy **chạy nền tự động** — không cần terminal thứ hai, teacher bấm "Câu tiếp theo" trên web là câu hỏi **tự động** xuống thiết bị.

Sau mỗi lần bật lại Pi, SSH vào và chạy:

```
ssh katespi@192.168.50.2
cd ~/pulsenet
./start_gateway.sh
```

### Cách biết gateway có đang hoạt động không

Nhìn badge **"Gateway: ..."** ở góc trên phải của trang web:

| Badge hiển thị | Ý nghĩa |
|---|---|
| 🟢 Gateway: ĐÃ NỐI THIẾT BỊ | Mọi thứ sẵn sàng |
| 🟡 Gateway: CHỜ THIẾT BỊ | Gateway chạy nhưng thiết bị chưa nối BLE (thiết bị chưa bật / cần reset) |
| 🔴 Gateway: CHƯA CHẠY | Chưa chạy `./start_gateway.sh` trên Pi |

Trong tab "Điều khiển & Giám sát" có dòng "✔ Đã đẩy tới thiết bị: Câu N" cho biết câu hỏi nào đã tới tay sinh viên.

### Lệnh thường dùng (trên Pi, trong `~/pulsenet`)

| Lệnh | Tác dụng |
|---|---|
| `./start_gateway.sh` | Khởi động gateway nền (đang chạy rồi thì chỉ báo) |
| `./stop_gateway.sh` | Dừng gateway |
| `./status_gateway.sh` | Kiểm tra trạng thái |
| `tail -f gateway/gateway.log` | Xem log gateway trực tiếp (Ctrl+C thoát) |

### Lưu ý

- Gateway **tự kết nối lại** khi thiết bị mất kết nối / bị reset — không cần làm gì.
- Nếu badge vàng "CHỜ THIẾT BỊ" kéo dài: kiểm tra thiết bị đã bật nguồn; thử nhấn nút **reset** trên ESP32.
- Vẫn muốn dùng menu tương tác (gửi tay, xem chi tiết)? Mở terminal SSH riêng và chạy `cd ~/pulsenet/gateway && .venv/bin/python send_ack.py`.
- Hiện gateway nối **1 thiết bị** (MAC cứng); đa thiết bị là bước nâng cấp tiếp theo.
