from flask import Flask, request, jsonify, render_template
import json
from datetime import datetime

app = Flask(__name__)

# 전역 변수로 데이터 저장
vehicle_data = None


@app.route('/')
def index():
    return render_template('index.html')


def load_data():
    global vehicle_data
    with open('data.json', 'r', encoding='utf-8') as file:
        vehicle_data = json.load(file)

    # 차량 번호를 키로 하는 딕셔너리로 변환
    vehicle_data = {item['VehicleNumber']: item for item in vehicle_data}


def format_date(date_list):
    return f"20{date_list[0]}-{date_list[1]}-{date_list[2]}"


@app.route('/filter_bookings', methods=['POST'])
def filter_bookings():
    data = request.json
    vehicle_number = data.get('vehicle_number')
    date_select = data.get('date_select')
    booking_status = data.get('booking_status', 'nondispatched')

    if vehicle_data is None:
        return jsonify({"error": "Data not loaded"}), 500

    if vehicle_number not in vehicle_data:
        return jsonify({"error": "Vehicle not found"}), 404

    vehicle_info = vehicle_data[vehicle_number]

    result = {
        "VehicleNumber": vehicle_number,
        "car_type": vehicle_info['car_type']
    }

    if booking_status == 'nondispatched':
        nondispatched_data = vehicle_info['nondispatched']
        if date_select:
            date_data = next((date for date in nondispatched_data['date_list'] if format_date(date[0]) == date_select),
                             None)
            if not date_data:
                return jsonify({"error": "No data for selected date"}), 404
            time_table = date_data[1]
        else:
            time_table = nondispatched_data['nondispatched_time_table']

        result["missed_call"] = nondispatched_data['missed_call']
        result["time_based_results"] = [
            {
                "시간": f"{int(hour):02d}:00~{(int(hour) + 1) % 24:02d}:00",
                "시간대별 미배차 건": count
            }
            for hour, count in time_table.items()
        ]
    else:  # dispatched
        dispatched_data = vehicle_info['dispatched']
        if date_select:
            date_data = next(
                (date for date in dispatched_data['dispatched_date_list'] if format_date(date[0]) == date_select), None)
            if not date_data:
                return jsonify({"error": "No data for selected date"}), 404
            time_table = date_data[1]
        else:
            time_table = dispatched_data['dispatched_time_table']

        result["patched_call"] = dispatched_data['patched_call']
        result["canceled_call"] = dispatched_data['canceled_call']
        result["time_based_results"] = [
            {
                "시간": f"{int(hour):02d}:00~{(int(hour) + 1) % 24:02d}:00",
                "시간대별 운송완료 건수": time_table.get(hour, {}).get('patched', 0),
                "시간대별 운송취소 건수": time_table.get(hour, {}).get('canceled', 0)
            }
            for hour in range(24)  # 모든 시간대를 포함
        ]

    return jsonify(result)

@app.route('/vehicles', methods=['GET'])
def get_vehicles():
    if vehicle_data is None:
        return jsonify({"error": "Data not loaded"}), 500

    vehicle_type = request.args.get('type')

    vehicle_counts = {}
    for data in vehicle_data.values():
        car_type = data['car_type']
        if car_type not in vehicle_counts:
            vehicle_counts[car_type] = {
                "nondispatched": 0,
                "dispatched": 0
            }
        vehicle_counts[car_type]["nondispatched"] += data['nondispatched']['missed_call']
        vehicle_counts[car_type]["dispatched"] += data['dispatched']['patched_call']

    if vehicle_type:
        if vehicle_type in vehicle_counts:
            return jsonify({vehicle_type: vehicle_counts[vehicle_type]})
        else:
            return jsonify({vehicle_type: {"nondispatched": 0, "dispatched": 0}})
    else:
        return jsonify(vehicle_counts)


if __name__ == '__main__':
    load_data()  # 애플리케이션 시작 시 데이터 로드
    app.run(debug=True)