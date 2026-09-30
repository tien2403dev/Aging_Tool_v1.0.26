# Lịch sử Alarm đọc trực tiếp từ log

Áp dụng cho Aging_Tool_PASS_USE(update) (3)(1).zip.

## Cài đặt
1. Đóng app đang chạy, giải nén gói này và chép đè theo đúng cấu trúc thư mục.
2. Giữ nguyên database và các file cấu hình. Không cần chạy migration mới.
3. Chọn Log Folder hợp lệ tại Machine Slot Yield hoặc File Management.
4. Search Alarm, bấm vào ô Slot Test. Trong khi log đang đọc, app hiển thị tiến trình.

## Luồng mở lịch sử
- Mỗi lần bấm Slot Test, worker đọc TXT trực tiếp từ Log Folder theo Machine, Slot và ngày Alarm. Không dùng dữ liệu `prime_data`, không dùng cache của Search và không lưu từng test vào database.
- Lấy tất cả file của ngày Alarm, đọc thêm ngày trước khi đủ tối đa 30 test của các Model liên quan; cặp 2 FAIL có Start/End lưu trong DB luôn được kiểm tra qua cả hai ngày khi cần.
- Đọc riêng 5 test mới nhất hiện tại của toàn slot để áp dụng ngoại lệ 5 PASS cho bốn quy tắc Yield.
- Cặp FAIL liên tiếp của Alarm cũ được đối chiếu với Start/End đã lưu và hai bản ghi FAIL liền kề; việc mở lịch sử của ngày cũ không bị mốc tạo Alarm 5 ngày tính từ hôm nay chặn.
- Các quy tắc Yield chỉ mở khi log hiện có còn tạo được chuỗi đủ 15/30 test và chưa bị ngoại lệ 5 PASS. Cửa sổ cùng Model bỏ qua Model khác xen giữa.
- Hiển thị toàn bộ PASS/FAIL trong mỗi cửa sổ khớp, kèm dropdown quy tắc/Model, số test, Yield, Target, Start/End. Nếu không còn chuỗi đúng với dòng Alarm, báo không có chuỗi, không hiển thị 30 test bất kỳ thay thế.
- Khi tạo Alarm mới, quy tắc 2 FAIL vẫn chỉ xét 5 ngày gần nhất. Dòng Alarm 2 FAIL cũ được giữ khi đã vượt mốc đó. Khi có thêm quy tắc Yield cùng ngày, giữ Start/End của cặp FAIL và gộp thêm lý do; nếu log không còn cặp đã lưu, người dùng vẫn thấy dòng nhưng bấm vào được thông báo không có chuỗi.

## Giới hạn
- Dòng Alarm cũ chỉ có dữ liệu tổng, nên các chuỗi Yield không thể khôi phục chính xác Target/Model đã đổi nếu cấu hình cũ không còn; việc mở lịch sử phản ánh log và Target hiện tại. Target 15/30 chung lấy từ dòng Alarm đã lưu.
- Lịch sử cần truy cập các file log gốc. Nếu file đã bị xóa, đổi tên ngày không khớp, hoặc folder không truy cập được, không thể dựng đủ chuỗi.
- Việc đọc log khi bấm một dòng cũ có thể mất thời gian trên ổ mạng; thao tác chạy trong worker để giao diện không bị treo.

## Kiểm tra
- Cú pháp Python của các file thay đổi.
- Dữ liệu giả lập: Alarm 2 FAIL cũ sau mốc 5 ngày, cặp vắt hai ngày, 30 PASS sau cặp trong ngày, log thay đổi khiến không còn cặp; 15 cùng Model có Model khác xen giữa, thiếu 15 test và 5 PASS hiện tại.
- SQLite tạm: Alarm 2 FAIL cũ không bị xóa khi tìm kiếm lại sau mốc 5 ngày.
- Chưa kiểm thử chạy PyQt5 trên Windows hoặc tốc độ ổ mạng thực tế.
