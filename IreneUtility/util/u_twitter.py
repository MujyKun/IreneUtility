from IreneUtility.Base import Base


class Twitter(Base):
    def __init__(self, *args):
        super().__init__(*args)
        
    async def update_status(self, context):
        self.ex.api.update_status(status=context)
        tweet = self.ex.api.user_timeline(user_id=f'{self.ex.keys.twitter_account_id}', count=1)[0]
        return f"https://twitter.com/{self.ex.keys.twitter_username}/status/{tweet.id}"

    async def delete_status(self, context):
        self.ex.api.destroy_status(context)

    async def recent_tweets(self, context):
        tweets = self.ex.api.user_timeline(user_id=f'{self.ex.keys.twitter_account_id}', count=context)
        final_tweet = ""
        for tweet in tweets:
            final_tweet += f"> **Tweet ID:** {tweet.id} | **Tweet:** {tweet.text}\n"
        return final_tweet


# self.ex.u_twitter = Twitter()
