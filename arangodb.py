import pandas as pd
from arango import ArangoClient
import json

# اتصال به ArangoDB
client = ArangoClient(hosts='http://localhost:8529')
sys_db = client.db('_system', username='root', password='')  # رمز عبورت رو اینجا وارد کن

# ایجاد دیتابیس اگه وجود نداشته باشه
if not sys_db.has_database('Hospital_Management'):
    sys_db.create_database('Hospital_Management')

# اتصال به دیتابیس hospital_management
db = client.db('Hospital_Management', username='root', password='')  # رمز عبورت رو اینجا وارد کن

# ایجاد مجموعه‌ها
collections = [
    'patients', 'doctors', 'staff', 'nurses', 'pharmacies', 'drugs', 'rooms', 'wards', 'interns', 'equipment'
]
edge_collections = ['prescriptions', 'appointments', 'patient_reports']

for col in collections:
    if not db.has_collection(col):
        db.create_collection(col)

for edge_col in edge_collections:
    if not db.has_collection(edge_col):
        db.create_collection(edge_col, edge=True)

# خواندن دیتاست
df = pd.read_csv('healthcare_dataset.csv').head(100) 

# تمیز کردن داده‌ها (حذف فاصله‌ها و تبدیل به حروف کوچک در ستون‌ها)
df.columns = df.columns.str.strip().str.lower()

# وارد کردن بیماران
patients = []
for _, row in df.iterrows():
    patient = {
        '_key': str(row['name']).replace(' ', '').lower(),  # کلید منحصر به فرد
        'name': row['name'],
        'age': row['age'],
        'gender': row['gender'],
        'blood_type': row['blood type'],
        'medical_condition': row['medical condition'],
        #'phone': '09123456789',  
        'address': 'Sample Address',  # داده نمونه
        'admission_date': row['date of admission'],
        'insurance_provider': row['insurance provider'],
        'room_number': row['room number'],
        'admission_type': row['admission type'],
        'medication': row['medication'],
        'test_results': row['test results'],
        'discharge_date': row['discharge date'],
        'room_number': str(row['room number']),
        'billing_amount': row['billing amount']
    }
    patients.append(patient)

db.collection('patients').insert_many(patients, overwrite=True)

# وارد کردن پزشکان (استخراج از ستون Doctor)
doctors = []
doctor_names = df['doctor'].unique()
for i, name in enumerate(doctor_names):
    doctor = {
        '_key': f'doc{i+1}',
        'name': name,
        'specialty': 'General Medicine',  # داده نمونه
        'phone': f'0912000{i+1:04d}'  # شماره نمونه
    }
    doctors.append(doctor)

db.collection('doctors').insert_many(doctors, overwrite=True)

# وارد کردن داروها (استخراج از ستون Medication)
drugs = []
drug_names = df['medication'].unique()
for i, name in enumerate(drug_names):
    drug = {
        '_key': f'drug{i+1}',
        'name': name,
        'type': 'Tablet',  # داده نمونه
        'dosage': '500mg',  # داده نمونه
        'price': 10.0 + i  # قیمت نمونه
    }
    drugs.append(drug)

db.collection('drugs').insert_many(drugs, overwrite=True)

# وارد کردن نسخه‌ها (رابطه بین بیماران، پزشکان و داروها)
prescriptions = []
for _, row in df.iterrows():
    patient_key = str(row['name']).replace(' ', '').lower()
    doctor = next(doc for doc in doctors if doc['name'] == row['doctor'])
    drug = next(d for d in drugs if d['name'] == row['medication'])
    prescription = {
        '_from': f'patients/{patient_key}',
        '_to': f'drugs/{drug["_key"]}',
        'doctor_id': f'doctors/{doctor["_key"]}',
        'date': row['date of admission'],
        'dosage': '500mg'  # داده نمونه
    }
    prescriptions.append(prescription)

db.collection('prescriptions').insert_many(prescriptions, overwrite=True)

# اضافه کردن داده‌های نمونه برای سایر مجموعه‌ها
# اتاق‌ها
rooms = [{'_key': str(i), 'type': 'Single', 'status': 'Occupied'} for i in df['room number'].unique()]
db.collection('rooms').insert_many(rooms, overwrite=True)

# بخش‌ها (نمونه)
wards = [{'_key': 'ward1', 'name': 'General Ward', 'location': 'First Floor'}]
db.collection('wards').insert_many(wards, overwrite=True)

# کارکنان (نمونه)
staff = [
    {'_key': 'staff1', 'name': 'Ali Rezaei', 'role': 'Receptionist', 'phone': '09121112233'},
    {'_key': 'staff2', 'name': 'Sara Mohammadi', 'role': 'Manager', 'phone': '09123334455'}
]
db.collection('staff').insert_many(staff, overwrite=True)

# پرستارها (نمونه)
nurses = [
    {'_key': 'nurse1', 'name': 'Maryam Hosseini', 'shift': 'Morning'},
    {'_key': 'nurse2', 'name': 'Narges Ahmadi', 'shift': 'Night'}
]
db.collection('nurses').insert_many(nurses, overwrite=True)

# تجهیزات (نمونه)
equipment = [
    {'_key': 'eq1', 'name': 'X-Ray Machine', 'type': 'Diagnostic', 'status': 'Available'},
    {'_key': 'eq2', 'name': 'Ventilator', 'type': 'Critical', 'status': 'In Use'}
]
db.collection('equipment').insert_many(equipment, overwrite=True)

# داروخانه (نمونه)
pharmacies = [{'_key': 'pharm1', 'name': 'Main Pharmacy', 'location': 'Ground Floor'}]
db.collection('pharmacies').insert_many(pharmacies, overwrite=True)

# رزروها (نمونه)
appointments = [
    {
        '_from': f'patients/{patients[0]["_key"]}',
        '_to': f'doctors/{doctors[0]["_key"]}',
        'date': '2024-05-01',
        'time': '10:00',
        'status': 'Scheduled'
    }
]
db.collection('appointments').insert_many(appointments, overwrite=True)

print("دیتابیس با موفقیت راه‌اندازی شد و داده‌ها وارد شدند!")