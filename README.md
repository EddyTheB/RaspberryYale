# RaspberryYale
Code that uses e-mail alerts from my Yale burglar alarm to trigger a raspberry-pi security camera.


Google APIs have default request limits per project. It looks like more than 1 request per second for a period over 100 seconds will lead to issues. The code by default checks emails every 5 seconds, and that should be fine. https://developers.google.com/analytics/devguides/reporting/core/v3/limits-quotas

## Acknowledgements
### For reading gmail stuff
This great blog post, and the couple of posts before it: http://wescpy.blogspot.co.uk/2015/08/accessing-gmail-from-python-plus-bonus.html

The gmail API documentation, especially the code snippets: https://developers.google.com/gmail/api/v1/reference/

The checkInternet function is entirely thanks to 7h3rAm's answer to this question: http://stackoverflow.com/questions/3764291/checking-network-connection
