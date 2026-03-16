from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
import pandas as pd
import numpy as np
import seaborn as sns

class TitanicModel:
    _instance = None
    
    def __init__(self):
        self.model = None
        self.dt = None
        self.features = ['pclass', 'sex', 'age', 'sibsp', 'parch', 'fare', 'alone']
        self.target = 'survived'
        self.titanic_data = sns.load_dataset('titanic')
        self.encoder = OneHotEncoder(handle_unknown='ignore')

    def _clean(self):
        self.titanic_data.drop(['alive', 'who', 'adult_male', 'class', 'embark_town', 'deck'], axis=1, inplace=True)
        self.titanic_data['sex'] = self.titanic_data['sex'].apply(lambda x: 1 if x == 'male' else 0)
        self.titanic_data['alone'] = self.titanic_data['alone'].apply(lambda x: 1 if x == True else 0)
        self.titanic_data.dropna(subset=['embarked'], inplace=True)
        onehot = self.encoder.fit_transform(self.titanic_data[['embarked']]).toarray()
        cols = ['embarked_' + str(val) for val in self.encoder.categories_[0]]
        onehot_df = pd.DataFrame(onehot, columns=cols)
        self.titanic_data = pd.concat([self.titanic_data, onehot_df], axis=1)
        self.titanic_data.drop(['embarked'], axis=1, inplace=True)
        self.features.extend(cols)
        self.titanic_data.dropna(inplace=True)

    def _train(self):
        X = self.titanic_data[self.features]
        y = self.titanic_data[self.target]
        self.model = LogisticRegression(max_iter=1000)
        self.model.fit(X, y)
        self.dt = DecisionTreeClassifier()
        self.dt.fit(X, y)
        
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._clean()
            cls._instance._train()
        return cls._instance

    def predict(self, passenger):
        passenger_df = pd.DataFrame(passenger, index=[0])
        passenger_df['sex'] = passenger_df['sex'].apply(lambda x: 1 if x == 'male' else 0)
        passenger_df['alone'] = passenger_df['alone'].apply(lambda x: 1 if x == True else 0)
        onehot = self.encoder.transform(passenger_df[['embarked']]).toarray()
        cols = ['embarked_' + str(val) for val in self.encoder.categories_[0]]
        onehot_df = pd.DataFrame(onehot, columns=cols)
        passenger_df = pd.concat([passenger_df, onehot_df], axis=1)
        passenger_df.drop(['embarked', 'name'], axis=1, inplace=True)
        die, survive = np.squeeze(self.model.predict_proba(passenger_df))
        return {'die': die, 'survive': survive}
    
    def feature_weights(self):
        importances = self.dt.feature_importances_
        return {feature: importance for feature, importance in zip(self.features, importances)} 
    
def initTitanic():
    TitanicModel.get_instance()