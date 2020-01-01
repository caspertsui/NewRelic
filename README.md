# New Relic complementation tools
## Reason
There is no simple way to get notification channel information such as Slack, email address and etc. for a specific monitor via New Relic REST APIs.

## Installation
```bash
pip install -r requirements.txt
```

## Execution
```bash
export NEW_RELIC_API_KEY=YOUR_API_KEY
python ./rest_api_data_consolidator.py
```

## Output
```bash
# Intermediate files
./data/*

# Pandas dataframe result CSV file
./result_dt.csv
```

## Reference
https://discuss.newrelic.com/t/feature-idea-how-to-get-notification-channel-information-for-a-synthetic-monitor-with-rest-api/90820/7
