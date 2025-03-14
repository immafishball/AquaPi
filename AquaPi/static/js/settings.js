$(document).ready(function() {
    // Initialize DataTable
    var table = $('#dataTable').DataTable({
        scrollX: true,
        responsive: true,
        autoWidth: true,
        responsive: true,
        order: [[11, 'desc']], // Default sort by timestamp column (index 8) in descending order
        buttons: [
            'copy', 'csv', 'excel', 'pdf', 'print'
        ],
        columns: [
            { data: 'ph_level', title: 'pH', render: $.fn.dataTable.render.number(',', '.', 3) },
            { data: 'ph_status', title: 'pH Status' },
            { data: 'temp_cels', title: 'Temp °C', render: $.fn.dataTable.render.number(',', '.', 3) },
            { data: 'temp_fah', title: 'Temp °F', render: $.fn.dataTable.render.number(',', '.', 3) },
            { data: 'temp_status', title: 'Temp Status' },
            { data: 'turbidity', title: 'Turbidity', render: $.fn.dataTable.render.number(',', '.', 3) },
            { data: 'turbidity_status', title: 'Turbidity Status' },
            { data: 'water_level', title: 'Water Level' },
            { data: 'operation', title: 'Operation' },
            { data: 'operation_status', title: 'Operation Status' },
            { data: 'detected_objects', title: 'Detected Objects' },
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

    // Function to fetch data and update the DataTable
    function fetchData() {
        // Save the current page index
        var currentPage = table.page();
    
        $.ajax({
            url: '/get_all_data',
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
                        operation: row[9],
                        operation_status: row[10],
                        detected_objects: row[11] || "None"
                    };
                });
    
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
                    operation: '',
                    operation_status: '',
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

$.ajax({
    url: '/get_all_data',
    method: 'GET',
    dataType: 'json',
    success: function(response) {
        console.log("Fetched data:", response); // Debug log
        if (!Array.isArray(response) || response.length === 0) {
            console.warn("No data received");
        }
        table.clear().rows.add(response).draw(false);
    },
    error: function(xhr, status, error) {
        console.error("AJAX Error:", status, error);
    }
});
