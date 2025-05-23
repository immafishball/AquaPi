$(document).ready(function() {
    // Initialize DataTable
    var table = $('#dataTable').DataTable({
        scrollX: true,
        responsive: true,
        autoWidth: true,
        responsive: true,
        order: [[10, 'desc']], // Default sort by timestamp column (index 8) in descending order
        buttons: [
            'copy', 'csv', 'excel', 'pdf', 'print'
        ],
        columns: [
            { data: 'ph_level', title: 'pH', render: $.fn.dataTable.render.number(',', '.', 3) },
            { 
                data: 'ph_status', 
                title: 'pH Status',
                render: function(data) {
                    let color = (data === "Acidic | Adding pH UP" || data === "Alkaline | Adding pH Down") ? 'red' : 'inherit';
                    return `<span style="color:${color};">${data}</span>`;
                }
            },
            { data: 'temp_cels', title: 'Temp °C', render: $.fn.dataTable.render.number(',', '.', 3) },
            { data: 'temp_fah', title: 'Temp °F', render: $.fn.dataTable.render.number(',', '.', 3) },
            { 
                data: 'temp_status', 
                title: 'Temp Status',
                render: function(data) {
                    let color = data === "Warning" ? 'orange' : (data === "Critical" ? 'red' : 'inherit');
                    return `<span style="color:${color};">${data}</span>`;
                }
            },      
            { data: 'turbidity', title: 'Turbidity', render: $.fn.dataTable.render.number(',', '.', 3) },
            { data: 'turbidity_status', title: 'Turbidity Status' },
            { data: 'water_level', title: 'Water Level' },
            { data: 'water_level_status', title: 'Water Level Status' },
            { data: 'detected_objects', title: 'Detected Fish' },
            { 
                data: 'timestamp', 
                title: 'Timestamp',
                render: function(data) {
                    var date = new Date(data);
                    return date.toLocaleString();
                },
                type: 'num', // Ensure the column is sorted as numeric
                // Use the timestamp value (in milliseconds) for sorting
                //render: function(data) {
                //    var date = new Date(data);
                //    return '<span data-order="' + data + '">' + date.toLocaleString() + '</span>';
                //}
            }
        ],
        columnDefs: [
            {
                targets: [0, 2, 3],  // Apply formatting to these columns
                render: function(data) {
                    return parseFloat(data).toFixed(3);
                }
            }
        ],
        stateSave: true,  // Save state to maintain pagination, search, etc.
        processing: true, // Show processing indicator
        serverSide: false, // Set to false since we're using client-side data
    });

    // Save the current page index
    var currentPage = table.page();

    // Add DataTable buttons manually
    new $.fn.dataTable.Buttons(table, {
        buttons: [
            { extend: 'copy', text: 'Copy' },
            { extend: 'csv', text: 'CSV' },
            { extend: 'excel', text: 'Excel' },
            { extend: 'pdf', text: 'PDF' },
            { extend: 'print', text: 'Print' }
        ]
    }).container().appendTo($('#dataTableButtons'));

    // Function to get query parameter value from URL
    function getQueryParam(param) {
        let urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(param);
    }

    // Function to fetch data and update the DataTable
    function fetchData() {
        let fishType = getQueryParam("fishType");
        let apiUrl = fishType ? `/get_all_data?fishType=${encodeURIComponent(fishType)}` : "/get_all_data";

        if (table.data().count() === 0) {
            $("#dataTable tbody").html(`
                <tr>
                    <td colspan="11" class="text-center" style="text-align: center; font-weight: bold; padding: 20px;">
                        Fetching data...
                    </td>
                </tr>
            `);
        }

        $.ajax({
            url: apiUrl,
            method: 'GET',
            dataType: 'json',
            success: function(response) {
                // Map the response data to DataTables format
                var data = response.map(function(row) {
                    return {
                        timestamp: row[0],
                        ph_level: row[1],
                        ph_status: row[2],
                        temp_cels: row[3],
                        temp_fah: row[4],
                        temp_status: row[5],
                        turbidity: row[6],
                        turbidity_status: row[7],
                        water_level: row[8],
                        water_level_status: row[9],
                        detected_objects: row[10] ? row[10] : "None"
                    };
                });
    
                // Store the current page index
                var currentPage = table.page();
                
                // Clear existing data, add new data, and redraw the table
                table.clear().rows.add(data).draw(false);  // Pass `false` to prevent full redraw
    
                // Restore the saved page index
                table.page(currentPage).draw(false);
            },
            error: function() {
                // Handle error and show failed data row
                table.clear().rows.add([{
                    timestamp: null,
                    ph_level: 'Failed to load data',
                    ph_status: '',
                    temp_cels: '',
                    temp_fah: '',
                    temp_status: '',
                    turbidity: '',
                    turbidity_status: '',
                    water_level: '',
                    water_level_status: '',
                    detected_objects: ''
                }]).draw(false);  // Prevent full redraw to keep pagination
            }
        });
    }
    
    // Fetch data on initial load
    fetchData();

    // Set interval for periodic updates (every 10 seconds)
    setInterval(fetchData, 10000);
});
