from flask import Blueprint, request, jsonify
from flask_restful import Api, Resource
from model.titanic import TitanicModel

titanic_api = Blueprint('titanic_api', __name__, url_prefix='/api/titanic')
api = Api(titanic_api)

class TitanicAPI:
    class _Predict(Resource):
        def post(self):
            passenger = request.get_json()
            titanicModel = TitanicModel.get_instance()
            response = titanicModel.predict(passenger)
            return jsonify(response)

    api.add_resource(_Predict, '/predict')