import gradio as gr
from arango import ArangoClient
import pandas as pd

# --- FIX 1: Establish a single, reusable database connection ---
# This is more efficient than connecting every time a query is run.
try:
    client = ArangoClient(hosts='http://localhost:8529')
    db = client.db('Hospital_Management', username='root', password='') # Enter your password here
except Exception as e:
    print(f"Failed to connect to ArangoDB: {e}")
    db = None

# --- This function is no longer needed after the fixes, I've commented it out ---
# def execute_aql_query(query):
#     ...

# تابع برای ساخت کوئری AQL بر اساس فیلترها
def build_aql_query(name, gender, medical_condition,doctor_name, insurance_provider, medication, test_results):
    # شروع کوئری پایه
    query = "FOR patient IN patients "
    
    # لیست فیلترها
    filters = []
    bind_vars = {} # Initialize bind_vars dictionary
    
    # افزودن فیلتر نام (جستجوی تقریبی)
    if name:
        filters.append(f'LIKE(patient.name, @name)')
        bind_vars['name'] = f"%{name}%"
    
    # افزودن فیلتر جنسیت
    if gender and gender != "همه":
        filters.append(f'patient.gender == @gender')
        bind_vars['gender'] = gender
    
    # افزودن فیلتر بیماری
    if medical_condition and medical_condition != "همه":
        filters.append(f'patient.Medical_Condition == @medical_condition')
        bind_vars['medical_condition'] = medical_condition
    
    # افزودن فیلتر بیمه
    if insurance_provider and insurance_provider != "همه":
        filters.append(f'patient.insurance_provider == @insurance_provider')
        bind_vars['insurance_provider'] = insurance_provider
    
    # افزودن فیلتر نتایج آزمایش
    if test_results and test_results != "همه":
        filters.append(f'LOWER(patient.test_results) == LOWER(@test_results)')
        bind_vars['test_results'] = test_results
    
    # افزودن فیلتر دارو (نیاز به JOIN با مجموعه prescriptions و drugs)
    if medication and medication != "همه":
        query += """
        FOR prescription IN prescriptions
        FILTER prescription._from == patient._id
        FOR drug IN drugs
        FILTER prescription._to == drug._id AND drug.name == @medication
        """
        bind_vars["medication"] = medication
    if doctor_name:
        # این کوئری فرعی، بیمارانی را پیدا می‌کند که پزشکی با نام مشابه برایشان نسخه ثبت کرده باشد
        filters.append("""
            patient._id IN (
                FOR p IN prescriptions
                    LET doc = DOCUMENT(p.doctor_id)
                    FILTER LIKE(doc.name, @doctor_name)
                    RETURN p._from
            )
        """)
        bind_vars['doctor_name'] = f"%{doctor_name}%"

    # اضافه کردن فیلترها به کوئری
    if filters:
        query += "FILTER " + " AND ".join(filters) + " "
    
    # مشخص کردن خروجی
    # --- FIX 2: Made the medication part of the RETURN dynamic ---
    # It now only tries to get the medication name if a medication was selected.
    # medication_return_aql = """
    #     (FOR p IN prescriptions
    #         FILTER p._from == patient._id
    #         FOR d IN drugs
    #             FILTER p._to == d._id AND d.name == @medication
    #         LIMIT 1
    #         RETURN d.name)[0]
    # """ if medication and medication != "همه" else "null"

    query += f"""
    LET doctor_name = FIRST(
        FOR p IN prescriptions
            FILTER p._from == patient._id
            LIMIT 1
            LET doc = DOCUMENT(p.doctor_id)
            RETURN doc.name
    )
    RETURN {{
        name: patient.name,
        age: patient.age,
        gender: patient.gender,
        doctor: doctor_name,
        medical_condition: patient.medical_condition,
        insurance_provider: patient.insurance_provider,
        medication: patient.medication,
        test_results: patient.test_results,
        admission_date: patient.admission_date,
        discharge_date: patient.discharge_date,
        billing_amount: patient.billing_amount,
        room_number: patient.room_number
    }}
    """
    
    return query, bind_vars

# تابع رابط کاربری برای فیلترها
def gradio_interface(name, gender, medical_condition,doctor_name, insurance_provider, medication, test_results):
    # --- FIX 3: Centralized and improved query execution and error handling ---
    if db is None:
        # Handle case where initial DB connection failed
        print("Database connection is not available.")
        return pd.DataFrame() # Return an empty dataframe

    query, bind_vars = build_aql_query(name, gender, medical_condition,doctor_name,insurance_provider, medication, test_results)
    
    try:
        # Execute the query directly here
        cursor = db.aql.execute(query, bind_vars=bind_vars)
        results = [doc for doc in cursor]

        if results:
            # Convert results to a DataFrame
            return pd.DataFrame(results)
        else:
            # If no results, return an empty DataFrame so the UI doesn't break
            return pd.DataFrame()

    except Exception as e:
        # If any error occurs, print it for debugging and return an empty DataFrame
        print(f"An error occurred while executing the query: {e}")
        return pd.DataFrame()

# گزینه‌های فیلترها (بر اساس دیتاست)
gender_options = ["همه", "Male", "Female"]
medical_condition_options = ["همه", "Cancer", "Obesity", "Diabetes", "Asthma", "Hypertension", "Arthritis"]
insurance_provider_options = ["همه", "Blue Cross", "Medicare", "Aetna", "Cigna", "UnitedHealthcare"]
medication_options = ["همه", "Paracetamol", "Ibuprofen", "Aspirin", "Penicillin", "Lipitor"]
test_results_options = ["همه", "Normal", "Abnormal", "Inconclusive"]
rtl_css = """
    #rtl_container { direction: rtl; }
#rtl_container .gradio-row { flex-direction: row-reverse !important; }
#rtl_container .gr-form > .gr-block > .label, #rtl_container .label { text-align: right !important; }
#rtl_container .gr-form { text-align: right; }
#rtl_container input::placeholder, #rtl_container textarea::placeholder { text-align: right; }
#rtl_container input, #rtl_container textarea { text-align: right; }
#rtl_container .multiselect__single, #rtl_container .multiselect__input { text-align: right !important; }
#rtl_container th, #rtl_container td { text-align: right !important; }
    """
# ایجاد رابط کاربری با Gradio
with gr.Blocks(css=rtl_css, elem_id="rtl_container") as demo:
    gr.Markdown("""<div style="direction:rtl;text-align: right;"> 
                <h1>رابط کاربری وب برای مدیریت بیمارستان</h1>
               </div> """)
    gr.Markdown("""<div style="direction:rtl;text-align:right;">
                <p>فیلترهای زیر را پر کنید تا داده‌های مورد نظر از دیتابیس بیمارستان استخراج شود</p>
                </div>""" )    
    with gr.Column(elem_classes=["rtl"]):
        with gr.Row():
            name_input = gr.Textbox(label="نام بیمار (یا بخشی از آن)", placeholder="مثال: Bobby")
            gender_input = gr.Dropdown(label="جنسیت", choices=gender_options, value="همه")
            medical_condition_input = gr.Dropdown(label="نوع بیماری", choices=medical_condition_options, value="همه")
    
        with gr.Row():
            insurance_provider_input = gr.Dropdown(label="شرکت بیمه", choices=insurance_provider_options, value="همه")
            medication_input = gr.Dropdown(label="نام دارو", choices=medication_options, value="همه")
            doctor_input = gr.Textbox(label="پزشک معالج",placeholder="نام دکتر")
            test_results_input = gr.Dropdown(label="نتایج آزمایش", choices=test_results_options, value="همه")
    
        submit_button = gr.Button("جستجو")
        output = gr.Dataframe(label="نتایج جستجو")
    
        submit_button.click(
        fn=gradio_interface,
        inputs=[name_input, gender_input, medical_condition_input,doctor_input, insurance_provider_input, medication_input, test_results_input],
        outputs=output
    )

# اجرای اپلیکیشن Gradio
demo.launch()   