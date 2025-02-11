from flask import Flask, render_template, request, Response
from datetime import datetime
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

    #Calculate save months if user inputs extra money. 

    months_paid = 0
    
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

        monthly_schedule.append({
            "Month": month,
            "Payment": round(monthly_payment,0),
            "Date": current_date.strftime("%Y-%m"),
            "Interest": round(interest,0),
            "Principal": round(principal,0),
            "Remaining Balance": round(remain_balance,0)
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
            yearly_schedule.append({
                "Year": year_summary["Year"],
                "Total Payment": round(year_summary["Total Payment"]),
                "Total Interest": round(year_summary["Total Interest"],0),
                "Total Principal": round(year_summary["Total Principal"],0),
                "Remaining Balance": round(year_summary["Remaining Balance"],0)
            })
            
            year_summary = {"Year": next_year, "Total Payment": 0, "Total Interest": 0, "Total Principal": 0, "Remaining Balance": remain_balance}


        months_paid += 1

        #Stop early when remain balance is paid off
        if remain_balance <= 0:
            break
    
    final_month = covert_number_to_month(current_date.month)
    final_year = current_date.year

    months_saved = n - months_paid

    return monthly_schedule,yearly_schedule,months_saved,total_interest,total_principal,final_month,final_year

def generate_pie_chart(total_principal,total_interest):
    if total_interest <=0 or total_principal <=0:
        return "Error: Total interest or principal is zero"
    
    fig = Figure()
    fig.set_facecolor("#f4f1ec")
    ax = fig.add_subplot(111)
    ax.pie(
        [total_principal, total_interest],
        labels=['Principal', 'Interest'],
        autopct='%1.0f%%',
        startangle=90,
        colors=['#83b8a1','#ffbd59'],
        textprops={'fontsize': 16, 'fontweight': 'bold'},
        wedgeprops= {"edgecolor":"#f4f1ec", 
                     'linewidth': 4, 
                     'antialiased': True}
    )
    ax.axis('equal')

    img = io.BytesIO()
    FigureCanvas(fig).print_png(img)  # Save the figure in memory
    img.seek(0)
    return base64.b64encode(img.getvalue()).decode('utf-8')

def generate_line_chart(schedule):
    df = pd.DataFrame(schedule)
    fig = Figure()
    fig.set_facecolor("#f4f1ec")
    ax = fig.add_subplot(1, 1, 1)
    ax.set_facecolor("#f4f1ec")

    df['Cumulative Interest'] = df['Total Interest'].cumsum()
    df['Cumulative Payment'] = df['Total Payment'].cumsum() + df['Cumulative Interest']

    ax.plot(df['Year'], df['Cumulative Payment'], label="Payment Paid", color="#83b8a1",linewidth=3)
    ax.plot(df['Year'], df['Cumulative Interest'], label="Interest Paid", color="#ffbd59",linewidth=3)
    ax.plot(df['Year'], df['Remaining Balance'], label="Remaining Balance", color="#000000",linewidth=2)

    ax.set_xlabel("Years", fontsize=12)
    ax.set_ylabel("Amount ($)", fontsize=12)
    ax.legend(fontsize=12,facecolor="#f4f1ec")

    img = io.BytesIO()
    FigureCanvas(fig).print_png(img)  # Save the figure in memory
    img.seek(0)
    return base64.b64encode(img.getvalue()).decode('utf-8')

@app.route('/calculate', methods=['POST'])
def handle_action():
    action = request.form.get('action')  # Determine which button was clicked

    if action == 'calculate':
        return calculate(request)  # Call the calculate handler
    elif action == 'compare':
        return compare(request)  # Call the compare handler
    else:
        return "Invalid action."

def calculate(request):
    
    try:
        # Get the values from the form
        amount1 = float(request.form['amount1'])
        rate1 = float(request.form['rate1'])
        years1 = int(request.form['years1'])
        down1 = float(request.form.get('down1', 0))
        extra1 = float(request.form.get('extra1', 0))
        start_month1 = int(request.form['start_month1'])
        start_year1 = request.form['start_year1']

        # Calculate the interest
        loan_amount = amount1 - down1
        
        monthly_payment = calculate_monthly_payment(loan_amount,rate1,years1)

        monthly_schedule,yearly_schedule,month_saved,total_interest,total_principal,final_month,final_year = amortization(loan_amount,extra1,rate1,years1,start_year1,start_month1)

        pie_chart = generate_pie_chart(round(total_principal,2),round(total_interest,2))

        line_chart = generate_line_chart(yearly_schedule)

        total_mortgage_payments = total_interest + loan_amount
        
        return render_template('result.html', monthly_payment=f"{monthly_payment:,.0f}", loan_amount = f"{loan_amount:,.0f}", total_interest = f"{total_interest:,.0f}", down = f"{down1:,.0f}", 
                               total_mortgage_payments = f"{total_mortgage_payments:,.0f}",month_saved = month_saved, monthly_schedule = monthly_schedule, 
                               yearly_schedule = yearly_schedule, final_month=final_month,final_year=final_year,pie_chart=pie_chart,line_chart=line_chart)

    except Exception as e:
        return f"Error: {e}"
    
def compare(request):
    
    try:
        # Scenario 1 Inputs
        amount1 = float(request.form['amount1'])
        rate1 = float(request.form['rate1'])
        years1 = int(request.form['years1'])
        down1 = float(request.form.get('down1', 0))
        extra1 = float(request.form.get('extra1', 0))
        start_month1 = request.form['start_month1']
        start_year1 = request.form['start_year1']

        # Scenario 2 Inputs
        amount2 = float(request.form['amount2'])
        rate2 = float(request.form['rate2'])
        years2 = int(request.form['years2'])
        down2 = float(request.form.get('down2', 0))
        extra2 = float(request.form.get('extra2', 0))
        start_month2 = request.form['start_month2']
        start_year2= request.form['start_year2']

        # Calculate for Scenario 1
        loan_amount1 = amount1 - down1
        monthly_payment1 = calculate_monthly_payment(loan_amount1, rate1, years1)
        monthly_schedule1,yearly_schedule1,month_saved1,total_interest1,total_principal1,final_month1,final_year1 = amortization(loan_amount1,extra1,rate1,years1,start_year1,start_month1)


        # Calculate for Scenario 2
        loan_amount2 = amount2 - down2
        monthly_payment2 = calculate_monthly_payment(loan_amount2, rate2, years2)
        monthly_schedule2,yearly_schedule2,month_saved2,total_interest2,total_principal2,final_month2,final_year2 = amortization(loan_amount2,extra2,rate2,years2,start_year2,start_month2)


        # Create charts for both scenarios
        pie_chart1 = generate_pie_chart(total_principal1, total_interest1)
        pie_chart2 = generate_pie_chart(total_principal2, total_interest2)

        # Render the comparison results
        return render_template(
            'compare.html',
            monthly_payment1=f"{monthly_payment1:,.0f}",
            total_interest1=f"{total_interest1:,.0f}",
            months_saved1=month_saved1,
            pie_chart1=pie_chart1,
            yearly_schedule1 = yearly_schedule1,
            final_month1=final_month1,
            final_year1=final_year1,

            monthly_payment2=f"{monthly_payment2:,.0f}",
            total_interest2=f"{total_interest2:,.0f}",
            months_saved2=month_saved2,
            pie_chart2=pie_chart2,
            yearly_schedule2 = yearly_schedule2,
            final_month2=final_month2,
            final_year2=final_year2,
        )
    except Exception as e:
        return f"Error: {e}"


@app.route('/download_csv', methods=['POST'])

def download_csv():

    schedule_type = request.form.get("schedule_type")
    
    schedule_data = request.form.get("schedule")

    df = pd.DataFrame(eval(schedule_data))

    csv_file = df.to_csv(index=False)

    filename = "amortization_schedule_yearly.csv" if schedule_type == "yearly" else "amortization_schedule_monthly.csv"

    return Response(csv_file,mimetype="text/csv",headers={"Content-Disposition": f'attachment; filename={filename}'})


if __name__=='__main__':
    app.run(debug=True)
