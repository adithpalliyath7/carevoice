-- Fictional demo seed — same 12 doctors as backend/app/data.py.
insert into hospitals (id, name, location, phone, emergency_phone, is_demo)
values ('demo-hospital-1', 'CareVoice General Hospital — Demo', 'Kochi, Kerala',
        '+91 484 000 0000', '+91 484 000 0001', true)
on conflict (id) do nothing;

insert into doctors (id, hospital_id, name, speciality, qualification, experience_years, languages, fee_inr, rating, location) values
('dr-anitha-nair','demo-hospital-1','Dr. Anitha Nair','General Physician','MBBS, MD',12,ARRAY['en','ml','hi'],500,4.8,'Kochi'),
('dr-rahul-menon','demo-hospital-1','Dr. Rahul Menon','Cardiology','MBBS, MD, DM',15,ARRAY['en','ml'],900,4.9,'Kochi'),
('dr-meera-iyer','demo-hospital-1','Dr. Meera Iyer','Cardiology','MBBS, MD, DM',10,ARRAY['en','ta','hi'],850,4.7,'Kochi'),
('dr-sana-khan','demo-hospital-1','Dr. Sana Khan','Dermatology','MBBS, MD',8,ARRAY['en','hi'],700,4.6,'Kochi'),
('dr-arun-kumar','demo-hospital-1','Dr. Arun Kumar','Orthopedics','MBBS, MS',14,ARRAY['en','ta','ml'],800,4.8,'Kochi'),
('dr-lakshmi-rao','demo-hospital-1','Dr. Lakshmi Rao','Paediatrics','MBBS, MD',11,ARRAY['en','te','hi'],600,4.9,'Kochi'),
('dr-priya-sharma','demo-hospital-1','Dr. Priya Sharma','Gynaecology','MBBS, MS',13,ARRAY['en','hi'],750,4.7,'Kochi'),
('dr-vikram-reddy','demo-hospital-1','Dr. Vikram Reddy','Neurology','MBBS, MD, DM',16,ARRAY['en','te'],1000,4.8,'Kochi'),
('dr-kavya-shetty','demo-hospital-1','Dr. Kavya Shetty','ENT','MBBS, MS',9,ARRAY['en','kn','ml'],650,4.6,'Kochi'),
('dr-farhan-ali','demo-hospital-1','Dr. Farhan Ali','Dental','BDS, MDS',7,ARRAY['en','hi','bn'],400,4.5,'Kochi'),
('dr-nisha-gupta','demo-hospital-1','Dr. Nisha Gupta','Ophthalmology','MBBS, MS',12,ARRAY['en','hi','bn'],700,4.7,'Kochi'),
('dr-thomas-jacob','demo-hospital-1','Dr. Thomas Jacob','General Physician','MBBS, MD',18,ARRAY['en','ml'],550,4.8,'Kochi')
on conflict (id) do nothing;
