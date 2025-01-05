export async function fetchSessionSummaries() {
    try {
        const response = await fetch('/sessions/list');
        const data = await response.json();
        const summaries = data.histories;
        let sessionSelect = document.getElementById("sessionSelect")
        // Clear existing options except the first one
        while (sessionSelect.options.length > 1) {
            sessionSelect.remove(1);
        }

        // Add new options
        summaries.forEach(summary => {
            const option = document.createElement('option');
            option.value = summary.session_id;
            option.text = summary.summary;
            sessionSelect.appendChild(option);
        });

        // Check if any summary is still "New conversation" and refetch if necessary
        const hasNewConversation = summaries.some(summary => summary.summary === "New conversation");
        if (hasNewConversation) {
            //setTimeout(fetchSessionSummaries, 5000); // Retry after 5 seconds
        }
    } catch (error) {
        console.error('Error fetching session summaries:', error);
    }
}
