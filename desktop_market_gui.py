import tkinter as tk
from tkinter import ttk, messagebox
import json

# Load product options
with open('./config/options.json', 'r') as file:
    opties = json.load(file)

# GUI state
segments = []

# App setup
root = tk.Tk()
root.title("Market Report Generator")
root.geometry("800x600")

# Frame for product selection
product_frame = ttk.LabelFrame(root, text="Select Product")
product_frame.pack(fill="x", padx=10, pady=5)

product_var = tk.StringVar()
product_dropdown = ttk.Combobox(product_frame, textvariable=product_var, values=opties["producten"])
product_dropdown.pack(padx=10, pady=5, fill="x")

# Frame for segment input
segment_frame = ttk.LabelFrame(root, text="Add Market Segment")
segment_frame.pack(fill="x", padx=10, pady=5)

variety_var = tk.StringVar()
origin_var = tk.StringVar()
note_var = tk.StringVar()

lowest_price_var = tk.DoubleVar()
highest_price_var = tk.DoubleVar()

market_quality_var = tk.StringVar()
current_demand_var = tk.StringVar()
demand_next_var = tk.StringVar()
arrivals_next_var = tk.StringVar()

# Row 1
row1 = tk.Frame(segment_frame)
row1.pack(fill="x", pady=2)
ttk.Label(row1, text="Variety/Color").pack(side="left", padx=5)
ttk.Combobox(row1, textvariable=variety_var, values=opties["product_specificatie"]).pack(side="left", padx=5)
ttk.Label(row1, text="Origin").pack(side="left", padx=5)
ttk.Combobox(row1, textvariable=origin_var, values=opties["landen_en_continenten"]).pack(side="left", padx=5)

# Row 2
row2 = tk.Frame(segment_frame)
row2.pack(fill="x", pady=2)
ttk.Label(row2, text="Note").pack(side="left", padx=5)
tk.Entry(row2, textvariable=note_var, width=80).pack(side="left", padx=5)

# Row 3
row3 = tk.Frame(segment_frame)
row3.pack(fill="x", pady=2)
ttk.Label(row3, text="Lowest Price").pack(side="left", padx=5)
tk.Entry(row3, textvariable=lowest_price_var, width=10).pack(side="left")
ttk.Label(row3, text="Highest Price").pack(side="left", padx=5)
tk.Entry(row3, textvariable=highest_price_var, width=10).pack(side="left")

# Row 4
row4 = tk.Frame(segment_frame)
row4.pack(fill="x", pady=2)
ttk.Label(row4, text="Market Quality").pack(side="left", padx=5)
ttk.Combobox(row4, textvariable=market_quality_var, values=["Good", "Medium", "Poor"]).pack(side="left")
ttk.Label(row4, text="Current Demand").pack(side="left", padx=5)
ttk.Combobox(row4, textvariable=current_demand_var, values=["High", "Medium", "Low"]).pack(side="left")

# Row 5
row5 = tk.Frame(segment_frame)
row5.pack(fill="x", pady=2)
ttk.Label(row5, text="Demand Next Week").pack(side="left", padx=5)
ttk.Combobox(row5, textvariable=demand_next_var, values=["↑", "→", "↓"]).pack(side="left")
ttk.Label(row5, text="Arrivals Next Week").pack(side="left", padx=5)
ttk.Combobox(row5, textvariable=arrivals_next_var, values=["↑", "→", "↓"]).pack(side="left")

# Add segment function
def add_segment():
    if not variety_var.get() or not origin_var.get():
        messagebox.showwarning("Missing Fields", "Variety and Origin are required.")
        return
    segment = {
        "variety": variety_var.get(),
        "origin": origin_var.get(),
        "note": note_var.get(),
        "lowest_price": lowest_price_var.get(),
        "highest_price": highest_price_var.get(),
        "market_quality": market_quality_var.get(),
        "current_demand": current_demand_var.get(),
        "demand_next": demand_next_var.get(),
        "arrivals_next": arrivals_next_var.get()
    }
    segments.append(segment)
    messagebox.showinfo("Segment Added", f"Added segment for {segment['variety']} from {segment['origin']}")

add_button = ttk.Button(root, text="Add Segment", command=add_segment)
add_button.pack(pady=10)

root.mainloop()
