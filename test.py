count = 0
current_day_weekday = 6  # 11月1日的星期数
for day in range(1, 31):
    weekday = (current_day_weekday + (day - 1)) % 7
    if weekday in (0, 2, 4):
        count += 1
print(count)