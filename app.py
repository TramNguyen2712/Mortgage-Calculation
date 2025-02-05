from flask import Flask, render_template, request, Response
from datetime import datetime, timedelta
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas 
import io
import base64

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

def covert_number_to_month(number):
    month_map = {
        1: "Jan",2: "Feb",3: "Mar",4: "Apr",5: "May",6: "Jun",
        7: "Jul",8: "Aug",9: "Sep",10: "Oct",11: "Nov",12: "Dec"
    }

    return month_map.get(number,"Jan")

def calculate_monthly_payment(P, interest_rate, years):
    # Calculate the anual rate
    i = (interest_rate/100)/12
    # Calculate the number payments
    n = years * 12
    # Calculate the monthly payment
    if i == 0:
        return "Error: Interest rate cannot be zero"
    return P * (i*(1+i)**n) / (((1+i)**n)-1)

def amortization(remain_balance, extra, interest_rate, years, start_year,start_month ):
    # Create a list to store the monthly and yearly payments
    monthly_schedule = []
    yearly_schedule = []

    #Create for pie chart

    total_interest = 0

    total_principal = 0 

    #Calculate save amount if user inputs extra money. 

    total_interest_saved = 0

    months_saved = 0
    
    i = (interest_rate/100)/12
    
    n = years * 12
    
    monthly_payment = calculate_monthly_payment(remain_balance,interest_rate,years)

    total_payment = monthly_payment + extra

    current_date = datetime(year=int(start_year), month=int(start_month), day=1)
    
    year_summary = {"Year": current_date.year, "Total Payment": 0, "Total Interest": 0, "Total Principal": 0, "Remaining Balance": remain_balance}

    for month in range(1,n+1): 
        interest = remain_balance * i
        principal = total_payment - interest

        if remain_balance < total_payment:
            total_payment = remain_balance + interest  # Final payment adjustment
            principal = remain_balance  # Pay off last remaining balance

        remain_balance = remain_balance - principal

        total_interest += interest
        total_principal += principal
        total_interest_saved += interest

        monthly_schedule.append({
            "Month": month,
            "Payment": round(monthly_payment,2),
            "Date": current_date.strftime("%Y-%m"),
            "Interest": round(interest,2),
            "Principal": round(principal,2),
            "Remaining Balance": round(remain_balance,2)
        })
        
        year_summary["Total Payment"] += total_payment
        year_summary["Total Interest"] += interest
        year_summary["Total Principal"] += principal
        
        # Move to the next month
        next_month = current_date.month + 1 if current_date.month < 12 else 1
        next_year = current_date.year if current_date.month < 12 else current_date.year + 1
        current_date = datetime(year=next_year, month=next_month, day=1)

        if next_month == 1:  # At the start of a new year, store the previous year's summary
            year_summary["Remaining Balance"] = remain_balance
            yearly_schedule.append(year_summary)
            year_summary = {"Year": next_year, "Total Payment": 0, "Total Interest": 0, "Total Principal": 0, "Remaining Balance": remain_balance}


        months_saved += 1

        #Stop early when remain balance is paid off
        if remain_balance <= 0:
            break
    
    final_month = covert_number_to_month(current_date.month)
    final_year = current_date.year

    return monthly_schedule,yearly_schedule,months_saved,total_interest_saved,total_interest,total_principal,final_month,final_year

def generate_pie_chart(total_principal,total_interest):
    fig = Figure()
    ax = fig.add_subplot(1, 1, 1)
    
    labels = ['Principal', 'Interest']
    sizes = [total_principal, total_interest]
    colors = ['#66b3ff', '#ff9999']
    
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors, startangle=140)
    ax.axis('equal')

    img = io.BytesIO()
    FigureCanvas(fig).print_png(img)  # Save the figure in memory
    return base64.b64encode(img.getvalue()).decode('utf-8')

def generate_line_chart(schedule):
    df = pd.DataFrame(schedule)
    fig = Figure()
    ax = fig.add_subplot(1, 1, 1)

    df['Cumulative Interest'] = df['Total Interest'].cumsum()
    df['Cumulative Payment'] = df['Total Payment'].cumsum() + df['Cumulative Interest']

    ax.plot(df['Year'], df['Cumulative Payment'], label="Payment Paid", color="blue")
    ax.plot(df['Year'], df['Cumulative Interest'], label="Interest Paid", color="red")
    ax.plot(df['Year'], df['Remaining Balance'], label="Remaining Balance", color="green")

    ax.set_xlabel("Years")
    ax.set_ylabel("Amount ($)")
    ax.set_title("Loan Breakdown Over Time")
    ax.legend()

    img = io.BytesIO()
    FigureCanvas(fig).print_png(img)  # Save the figure in memory
    return base64.b64encode(img.getvalue()).decode('utf-8')

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        # Get the values from the form
        amount = float(request.form['amount'])
        interest_rate = float(request.form['rate'])
        years = int(request.form['years'])
        down = float(request.form.get('down', 0))
        extra = float(request.form.get('extra', 0))
        start_month = request.form['start_month']
        start_year = request.form['start_year']

        # Calculate the interest
        loan_amount = amount - down
        
        monthly_payment = calculate_monthly_payment(loan_amount,interest_rate,years)

        monthly_schedule,yearly_schedule,month_saved,total_interest_saved,total_interest,total_principal,current_date = amortization(loan_amount,extra,interest_rate,years,start_year,start_month)

        pie_chart = generate_pie_chart(total_principal,total_interest)

        line_chart = generate_line_chart(yearly_schedule)

        total_mortgage_payments = total_interest + loan_amount
        
        return render_template('result.html', monthly_payment=round(monthly_payment,2), loan_amount = loan_amount, total_interest = round(total_interest,2), down = down, 
                               total_mortgage_payments = round(total_mortgage_payments,2), total_interest_saved=round(total_interest_saved, 2),month_saved = month_saved, schedule = monthly_schedule, 
                               current_date=current_date,pie_chart=pie_chart,line_chart=line_chart)

    except Exception as e:
        return f"Error: {e}"

@app.route('/download_csv', methods=['POST'])

def download_csv():

    schedule_data = request.form.get("schedule")

    df = pd.DataFrame(eval(schedule_data))

    csv_file = df.to_csv(index=False)

    return Response(csv_file,mimetype="text/csv",headers={"Content-Disposition": 'attachment; filename="amortization_monthly.csv"'})


if __name__=='__main__':
    app.run(debug=True)
