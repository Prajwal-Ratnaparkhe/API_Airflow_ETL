from airflow import DAG
from datetime import timedelta, datetime, timezone
from airflow.providers.http.sensors.http import HttpSensor
import json
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.operators.python import PythonOperator
import pandas as pd


def kelvin_to_celsius(temp_in_kelvin):
    temp_in_celsius = temp_in_kelvin - 273.15
    return temp_in_celsius

def transform_load_data(task_instance):
    data = task_instance.xcom_pull(task_ids="extract_weather_data")
    city = data["name"]
    weather_description = data["weather"][0]['description']
    temp_celsius = kelvin_to_celsius(data["main"]["temp"])
    feels_like_celsius= kelvin_to_celsius(data["main"]["feels_like"])
    min_temp_celsius = kelvin_to_celsius(data["main"]["temp_min"])
    max_temp_celsius = kelvin_to_celsius(data["main"]["temp_max"])
    pressure = data["main"]["pressure"]
    humidity = data["main"]["humidity"]
    wind_speed = data["wind"]["speed"]
    time_of_record = datetime.fromtimestamp(data['dt'] + data['timezone'], tz=timezone.utc)
    sunrise_time = datetime.fromtimestamp(data['sys']['sunrise'] + data['timezone'], tz=timezone.utc)
    sunset_time = datetime.fromtimestamp(data['sys']['sunset'] + data['timezone'], tz=timezone.utc)

    transformed_data = {"City": city,
                        "Description": weather_description,
                        "Temperature (F)": temp_celsius,
                        "Feels Like (F)": feels_like_celsius,
                        "Minimun Temp (F)":min_temp_celsius,
                        "Maximum Temp (F)": max_temp_celsius,
                        "Pressure": pressure,
                        "Humidty": humidity,
                        "Wind Speed": wind_speed,
                        "Time of Record": time_of_record,
                        "Sunrise (Local Time)":sunrise_time,
                        "Sunset (Local Time)": sunset_time                        
                        }
    transformed_data_list = [transformed_data]
    df_data = pd.DataFrame(transformed_data_list)
    aws_credentials = {"key": "xxxxxxxxxxxxxxxxxx", "secret": "xxxxxxxxxxxxxxxxxxxxxxxxxxx", "token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                       }

    now = datetime.now()
    dt_string = now.strftime("%d%m%Y%H%M%S")
    dt_string = 'current_weather_data_Pune' + dt_string
    df_data.to_csv(f"s3://weatherapi-airflow-etl-yml/{dt_string}.csv", index=False, storage_options=aws_credentials)



default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 8),
    'email': ['myemail@domain.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=2)
}



with DAG('weather_dag',
        default_args=default_args,
        schedule_interval = '@hourly',
        catchup=False) as dag:


        is_weather_api_ready = HttpSensor(
        task_id ='is_weather_api_ready',
        http_conn_id='weathermap_api',
        endpoint='/data/2.5/weather?q=Pune&appid=cea3f11f0088d54f3cba2ebd9c9ed7e1',
        )


        extract_weather_data = SimpleHttpOperator(
        task_id = 'extract_weather_data',
        http_conn_id = 'weathermap_api',
        endpoint='/data/2.5/weather?q=Pune&appid=cea3f11f0088d54f3cba2ebd9c9ed7e1',
        method = 'GET',
        response_filter= lambda r: json.loads(r.text),
        log_response=True,
        )

        transform_load_weather_data = PythonOperator(
        task_id= 'transform_load_weather_data',
        python_callable=transform_load_data
        )



        is_weather_api_ready >> extract_weather_data >> transform_load_weather_data