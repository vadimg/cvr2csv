# San Francisco raw ballot data to CSV

Converts Raw Ballot data (CVR JSON format) to a CSV file. The data may be obtained from https://sfelections.sfgov.org/november-8-2022-election-results-detailed-reports by downloading and unzipping the "Cast Vote Record (Raw data) - JSON".

The CSV file has a column for every ballot choice. This is straightforward except in the following cases:

* For ballot questions with multiple votes, the choices will be listed as separate columns. For example, if the choice is "School Board", the columns will be "School Board: CHOICE A", "School Board: CHOICE B", etc, up to the maximum amount of votes allowed for that ballot question. Note that there is no preference between choices, ie A is not ranked above B.
* For ranked ballots, the choices will be listed as separate columns with ranks. For example, if the choice is "Supervisor", the columns will be "Supervisor: RANK 1", "Supervisor: RANK 2", etc, up to the maximum amount of ranked choice votes you can select for that ballot question.
* If a voter does not fill out a rank n but does fill out a rank n+1, this is counted by the ballot system as if the voter had filled out rank n. This converter will simplify this by assigning the vote for rank n+1 to rank n.
* If a voter has submitted a ballot page but did not vote for a ballot question, that cell will contain "[-]" to denote the lack of a vote.

NOTE: Each row in the CSV is not a voter, it is a ballot page. There is no way to associate ballot pages for the same voter with each other, so it's only possible to do analysis on ballot questions that happened to be on the same ballot page.


## Web interface

If you run `python -m http.server` and go to `http://localhost:8000`, you will be able to map different types of voters (eg, a voter who voted for Measure D and against Measure E).

This should just work, as all processed data has been committed. To update the data, run:

* cvr2csv.py on the latest raw CVR data.
* split_votercard_into_pages.py. This splits the votercard csv into pages, which is required for the web app (otherwise, it'd be way too slow).
* sov.py on the latest "Statement of the Vote" excel file.

Both of the raw data sources can be downloaded from: https://sfelections.sfgov.org/november-8-2022-election-results-detailed-reports
