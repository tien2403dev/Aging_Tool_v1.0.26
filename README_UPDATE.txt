Aging Tool - Alarm / Machine Slot Yield / Gmail sync update

1. TAB Alarm reads and displays the same Machine Slot Yield Alarm data source.
2. Added synchronized metrics:
   - Total Test
   - PASS
   - FAIL
   - Yield
   - Last 15 / Target 15
   - Last 30 / Target 30
   - Alarm Reason
   - SCRAP CODE / Model
3. Machine Slot Yield Alarm database stores these metrics when Search is performed.
4. Existing databases are upgraded automatically by AlarmRepository.
5. Gmail Machine Slot Yield content uses the same stored Alarm values as TAB Alarm.
6. Gmail includes Date, Machine, Slot, Start/End, Total Test, PASS, FAIL, Yield, Last 15/30, Target 15/30, SCRAP CODE, Model and Reason.
7. Slot Fail email rendering is kept unchanged.
8. Customize Email is synchronized correctly:
   - Subject is saved and used when sending.
   - Heading is saved and included in HTML/Text email.
   - Closing is saved and included in HTML/Text email.
   - Body Preview now displays the saved Heading and Closing.
   - After Save, Body Preview reloads so it immediately matches the saved template.
9. Send Mail and Auto Send Mail both use the same saved Mail Template from database.

IMPORTANT:
After replacing the project, run Search in Machine Slot Yield once for the required date range. This refreshes the Alarm database with the current Machine Slot Yield calculations.
