// scripts/utils.js
export function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
export function formatTimestampForFrontend(backendTimestamp) {
    
    //Converts a backend timestamp (ISO 8601 format) to the format 
    //expected by the frontend ("MM/DD/YYYY, HH:MM:SS AM/PM").
    
    const date = new Date(backendTimestamp);
  
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const year = date.getFullYear();
    const hours = String(date.getHours() % 12 || 12).padStart(2, '0'); // 12-hour format
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    const ampm = date.getHours() >= 12 ? 'PM' : 'AM';
  
    return `${month}/${day}/${year}, ${hours}:${minutes}:${seconds} ${ampm}`;
  }
export function formatTimestamp(utcString) {
    // Parse the UTC string
    const [datePart, timePart] = utcString.split(', ');
    const [month, day, year] = datePart.split('/');
    let [hours, minutes, seconds] = timePart.split(':');
    const [secondsPart, ampm] = seconds.split(' ');
    seconds = secondsPart;

    // Convert to 24-hour format for Date object
    if (ampm === 'PM' && hours !== '12') hours = parseInt(hours, 10) + 12;
    if (ampm === 'AM' && hours === '12') hours = '00';

    // Create Date object in UTC
    const date = new Date(Date.UTC(year, month - 1, day, hours, minutes, seconds));

    // Format using locale's preferred hour format
    return date.toLocaleTimeString(undefined, { // returns local timezone time
        hour12: undefined, // retuns format based on locale
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}