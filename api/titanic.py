from flask import Blueprint, request, jsonify
from flask_restful import Api, Resource
from model.titanic import TitanicModel
import logging
import traceback

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

titanic_api = Blueprint('titanic_api', __name__, url_prefix='/api/titanic')
api = Api(titanic_api)

class TitanicAPI:
    class _Predict(Resource):
        def post(self):
            """Handle POST requests for Titanic survival prediction"""
            logger.info("Received prediction request")
            
            try:
                # Get JSON data from request
                passenger = request.get_json()
                
                if not passenger:
                    logger.warning("No JSON data received")
                    return jsonify({"error": "No data provided"}), 400
                
                logger.info(f"Passenger data received: {passenger}")
                
                # Validate required fields
                required_fields = ['pclass', 'sex', 'age', 'fare', 'sibsp', 'parch', 'embarked', 'alone']
                missing_fields = [field for field in required_fields if field not in passenger]
                
                if missing_fields:
                    logger.warning(f"Missing required fields: {missing_fields}")
                    return jsonify({
                        "error": f"Missing required fields: {missing_fields}"
                    }), 400
                
                # Get model instance and make prediction
                try:
                    titanicModel = TitanicModel()
                    response = titanicModel.predict(passenger)
                    
                    logger.info(f"Prediction successful: {response}")
                    return jsonify(response)
                    
                except Exception as e:
                    logger.error(f"Model prediction error: {str(e)}")
                    logger.error(traceback.format_exc())
                    return jsonify({
                        "error": f"Model prediction failed: {str(e)}"
                    }), 500
                
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                logger.error(traceback.format_exc())
                return jsonify({
                    "error": f"Internal server error: {str(e)}"
                }), 500
        
        def get(self):
            """Handle GET requests (for testing)"""
            logger.info("Received GET request")
            return jsonify({
                "message": "Titanic Prediction API",
                "usage": "Send POST request with passenger data",
                "example": {
                    "name": "Test Passenger",
                    "pclass": 2,
                    "sex": "female",
                    "age": 25,
                    "fare": 16.00,
                    "sibsp": 0,
                    "parch": 0,
                    "embarked": "S",
                    "alone": False
                }
            })

    class _Health(Resource):
        """Health check endpoint"""
        def get(self):
            try:
                # Test if model is loaded
                model = TitanicModel()
                return jsonify({
                    "status": "healthy",
                    "model_loaded": True,
                    "features": model.features
                })
            except Exception as e:
                return jsonify({
                    "status": "unhealthy",
                    "error": str(e)
                }), 500

    class _FeatureWeights(Resource):
        """Get feature importance weights"""
        def get(self):
            try:
                model = TitanicModel()
                weights = model.feature_weights()
                return jsonify(weights)
            except Exception as e:
                return jsonify({"error": str(e)}), 500

# Register resources
api.add_resource(TitanicAPI._Predict, '/predict')
api.add_resource(TitanicAPI._Health, '/health')
api.add_resource(TitanicAPI._FeatureWeights, '/features')