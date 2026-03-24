from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
import pandas as pd
import numpy as np
import seaborn as sns
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TitanicModel:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            logger.info("Creating new TitanicModel instance")
            cls._instance = super(TitanicModel, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        logger.info("Initializing TitanicModel")
        self.model = None
        self.dt = None
        self.features = ['pclass', 'sex', 'age', 'sibsp', 'parch', 'fare', 'alone']
        self.target = 'survived'
        
        try:
            self.titanic_data = sns.load_dataset('titanic')
            logger.info(f"Loaded titanic dataset with {len(self.titanic_data)} rows")
        except Exception as e:
            logger.error(f"Failed to load titanic dataset: {e}")
            raise
            
        self.encoder = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
        self._clean()
        self._train()
        self._initialized = True

    def _clean(self):
        """Clean and prepare the dataset"""
        logger.info("Cleaning dataset")
        
        # Drop unnecessary columns
        self.titanic_data.drop(['alive', 'who', 'adult_male', 'class', 'embark_town', 'deck'], 
                               axis=1, inplace=True, errors='ignore')
        
        # Convert categorical to numeric
        self.titanic_data['sex'] = self.titanic_data['sex'].apply(lambda x: 1 if x == 'male' else 0)
        self.titanic_data['alone'] = self.titanic_data['alone'].apply(lambda x: 1 if x == True else 0)
        
        # Handle embarked
        self.titanic_data.dropna(subset=['embarked'], inplace=True)
        
        # One-hot encode embarked
        onehot = self.encoder.fit_transform(self.titanic_data[['embarked']])
        cols = ['embarked_' + str(val) for val in self.encoder.categories_[0]]
        onehot_df = pd.DataFrame(onehot, columns=cols, index=self.titanic_data.index)
        
        self.titanic_data = pd.concat([self.titanic_data, onehot_df], axis=1)
        self.titanic_data.drop(['embarked'], axis=1, inplace=True)
        
        # Update features list
        self.features.extend(cols)
        
        # Drop any remaining NaN values
        initial_len = len(self.titanic_data)
        self.titanic_data.dropna(inplace=True)
        logger.info(f"Dropped {initial_len - len(self.titanic_data)} rows with NaN values")
        logger.info(f"Final dataset has {len(self.titanic_data)} rows with features: {self.features}")

    def _train(self):
        """Train the model"""
        logger.info("Training model")
        X = self.titanic_data[self.features]
        y = self.titanic_data[self.target]
        
        # Train Logistic Regression
        self.model = LogisticRegression(max_iter=1000, random_state=42)
        self.model.fit(X, y)
        logger.info(f"Logistic Regression training complete. Score: {self.model.score(X, y):.3f}")
        
        # Train Decision Tree for feature importance
        self.dt = DecisionTreeClassifier(random_state=42, max_depth=5)
        self.dt.fit(X, y)
        logger.info(f"Decision Tree training complete. Score: {self.dt.score(X, y):.3f}")

    def predict(self, passenger):
        """
        Predict survival probability for a passenger
        
        Args:
            passenger: dict with keys matching the features
            
        Returns:
            dict with 'die' and 'survive' probabilities
        """
        logger.info(f"Making prediction for passenger: {passenger.get('name', 'Unknown')}")
        
        # Create dataframe from passenger data
        passenger_df = pd.DataFrame([passenger])
        
        # Convert categorical to numeric
        passenger_df['sex'] = passenger_df['sex'].apply(lambda x: 1 if x == 'male' else 0)
        passenger_df['alone'] = passenger_df['alone'].apply(lambda x: 1 if x == True else 0)
        
        # One-hot encode embarked
        onehot = self.encoder.transform(passenger_df[['embarked']])
        cols = ['embarked_' + str(val) for val in self.encoder.categories_[0]]
        onehot_df = pd.DataFrame(onehot, columns=cols, index=passenger_df.index)
        
        # Combine and drop unnecessary columns
        passenger_df = pd.concat([passenger_df, onehot_df], axis=1)
        passenger_df.drop(['embarked', 'name'], axis=1, inplace=True, errors='ignore')
        
        # Ensure all features are present
        for feature in self.features:
            if feature not in passenger_df.columns:
                passenger_df[feature] = 0
                logger.warning(f"Feature {feature} not found in passenger data, defaulting to 0")
        
        # Reorder columns to match training data
        passenger_df = passenger_df[self.features]
        
        # Make prediction
        try:
            probabilities = self.model.predict_proba(passenger_df)[0]
            # Assuming model.classes_ gives [0, 1] where 0 = died, 1 = survived
            die_prob = float(probabilities[0])
            survive_prob = float(probabilities[1])
            
            logger.info(f"Prediction complete - Die: {die_prob:.3f}, Survive: {survive_prob:.3f}")
            return {'die': die_prob, 'survive': survive_prob}
            
        except Exception as e:
            logger.error(f"Error making prediction: {e}")
            raise
    
    def feature_weights(self):
        """Return feature importance from decision tree"""
        importances = self.dt.feature_importances_
        return {feature: float(importance) for feature, importance in zip(self.features, importances)}
    
def initTitanic():
    """Initialize the Titanic model singleton"""
    logger.info("Initializing Titanic model from initTitanic()")
    return TitanicModel()