import pandas as pd
from lenskit.als import BiasedMFScorer
from lenskit.basic import BiasScorer, PopScorer, RandomScorer
from lenskit.knn import ItemKNNScorer, UserKNNScorer
from lenskit.batch import recommend
from lenskit.data import from_interactions_df
from lenskit.pipeline import topn_pipeline


_MODELS = {
    'popular':   (PopScorer,      {}),
    'random':    (RandomScorer,   {}),
    'bias':      (BiasScorer,     {}),
    'item_knn':  (ItemKNNScorer,  {'nnbrs': 20}),
    'user_knn':  (UserKNNScorer,  {'nnbrs': 20}),
    'biased_mf': (BiasedMFScorer, {'features': 20, 'iterations': 20, 'reg': 0.1}),
}


class Recommender:
    def __init__(
        self,
        users: list,
        model: str = 'popular',
        n: int = 10,
        **model_kwargs,
    ):
        if model not in _MODELS:
            raise ValueError(f"Unknown model '{model}'. Options: {list(_MODELS)}")

        self.users = users
        self.n = n
        self._pipeline = self._build_pipeline(model, model_kwargs)

    def _build_pipeline(self, model_name: str, kwargs: dict):
        cls, defaults = _MODELS[model_name]
        scorer = cls(**{**defaults, **kwargs})

        data = pd.read_csv('data/user_ratings.tsv', sep='\t')
        data = data.rename(columns={
            'USERID': 'user_id',
            'MOVIEID': 'item_id',
            'RATING': 'rating',
        })
        data['timestamp'] = pd.Timestamp('2000-01-01')

        pipeline = topn_pipeline(scorer, self.n)
        pipeline.train(from_interactions_df(data))
        return pipeline

    def recs(self) -> pd.DataFrame:
        return recommend(self._pipeline, self.users, self.n)


if __name__ == '__main__':
    r = Recommender(users=[5], model='popular', n=10)
    for key, items in r.recs():
        print(key.user_id, items.to_df())
