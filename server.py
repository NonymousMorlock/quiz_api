import json
import os
import os.path
import datetime
from typing import Tuple

from dateutil import parser, tz

from flask import Flask, request, jsonify, abort, Response

app = Flask(__name__)


def error(e: Exception) -> tuple[Response, int]:
    print(e.with_traceback(e.__traceback__))
    return jsonify({'message': 'error occurred', 'action': 'Contact the administrator', 'details': str(e)}), 500


def get_files() -> list[str]:
    try:
        return [name for name in os.listdir('db') if os.path.isfile(os.path.join('db', name))]
    except FileNotFoundError:
        # create the db/ folder
        os.mkdir('db')
        return []


@app.post('/quizzes')
def api():
    try:
        data = request.get_json()

        question = data.get('question')
        options = data.get('options')
        answer = data.get('answer')  # this is the index of the correct answer
        # answer must be an integer
        if answer is not None:
            answer = int(answer)
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        if not question or not options or not answer or not start_date or not end_date:
            missing_fields = []
            if not question:
                missing_fields.append('question')
            if not options:
                missing_fields.append('options')
            if not answer:
                missing_fields.append('answer')
            if not start_date:
                missing_fields.append('start_date')
            if not end_date:
                missing_fields.append('end_date')

            # sample start_date
            # 2021-01-01T00:00:00.000Z

            message = 'Missing required fields: ' + ', '.join(missing_fields)
            return jsonify({'message': message}), 400

        # check the db/ folder and find out how many files are there, and store the next file name as the next number
        # e.g. if there are 3 files, then the next file name is 4
        # then create a file with that name and store the data in that file
        next_file_name = len(get_files()) + 1

        with open(f'db/{next_file_name}.json', 'w') as f:
            f.write(json.dumps({
                'id': next_file_name,
                'question': question,
                'options': options,
                'answer': answer,
                'start_date': start_date,
                'end_date': end_date
            }))

        return jsonify({'success': True})
    except Exception as e:
        return error(e)


@app.get('/quizzes/active')
def get_active_quiz():
    """ the quiz that is currently within its start and end time
    if there is no quiz, return None
    if there is more than one quiz, return the first one

    get all the files in the db/ folder
    for each file, read the file and check if the current time is within the start and end time
    if it is, return that quiz
    """

    try:
        files = get_files()
        for file in files:
            with open(f'db/{file}', 'r') as f:
                data = json.loads(f.read())
                start_date = data.get('start_date')
                end_date = data.get('end_date')

                time_zone = parser.parse(start_date).tzname()
                start_date = parser.parse(start_date).replace(tzinfo=tz.gettz(time_zone))
                end_date = parser.parse(end_date).replace(tzinfo=tz.gettz(time_zone))
                current_date = datetime.datetime.now().replace(tzinfo=tz.gettz(time_zone))

                if start_date <= current_date <= end_date:
                    return jsonify(data)

        return jsonify(None)
    except Exception as e:
        return error(e)


@app.get('/quizzes/<int:quiz_id>/result')
def get_result(quiz_id):
    try:
        filenames = get_files()
        for filename in filenames:
            with open(f'db/{filename}', 'r') as file:
                file_data = json.loads(file.read())
                if file_data['id'] != quiz_id:
                    continue
                end_time = parser.parse(file_data['end_date'])
                timezone = end_time.tzname()
                current_time = datetime.datetime.now().replace(tzinfo=tz.gettz(timezone))
                end_time = end_time.replace(tzinfo=tz.gettz(timezone))

                if current_time > end_time + datetime.timedelta(minutes=5):
                    return jsonify(file_data)
                else:
                    remaining_time = (end_time - current_time).total_seconds()

                    return jsonify({'message': f'Result not available yet, wait {remaining_time}s more'}), 404

    except Exception as e:
        error(e)


@app.get('/quizzes/all')
def get_all_quizzes():
    try:
        filenames = get_files()
        files = []
        for filename in filenames:
            with open(f'db/{filename}', 'r') as file:
                file_data: dict = json.loads(file.read())
                file_data.pop('answer')
                files.append(file_data)
        return jsonify(files)
    except Exception as e:
        return error(e)


if __name__ == '__main__':
    app.run(debug=True)
