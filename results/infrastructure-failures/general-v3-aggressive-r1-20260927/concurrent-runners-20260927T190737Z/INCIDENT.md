Concurrent runner incident

The quota watcher started a second runner at 2026-09-27T19:02:32Z during the manual resume. Both wrote to duration-laya, duration-baseline, and dotenv-von workspaces. These trials are invalid regardless of scores and were archived for a fresh rerun. The interrupted dotenv-baseline was also archived. Duration-von had only one session and was preserved. Both process trees were stopped before archiving. The reported 7/21 duration-laya result occurred during concurrent workspace writes and is not a valid accuracy result.
