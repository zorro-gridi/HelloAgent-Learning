def calculate_total_cost(attendances, price_per_attendance):
    """Calculate the total cost based on the number of attendances and price per attendance.
    
    Args:
        attendances (int): Number of times attended.
        price_per_attendance (int or float): Cost per attendance.
    
    Returns:
        float: Total cost.
    """
    return attendances * price_per_attendance

total_cost = calculate_total_cost(12, 40)
print(total_cost)