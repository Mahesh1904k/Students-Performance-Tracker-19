// Helper functions for inline error display
function showInlineError(fieldName, message) {
    // Create error element if it doesn't exist
    let errorElement = document.getElementById(fieldName + '_error');
    if (!errorElement) {
        errorElement = document.createElement('div');
        errorElement.id = fieldName + '_error';
        errorElement.className = 'text-danger mt-1';
        // Find the input field and insert the error after it
        const inputField = document.getElementById(fieldName);
        if (inputField) {
            inputField.parentNode.insertBefore(errorElement, inputField.nextSibling);
            // Add Bootstrap's is-invalid class to the input field
            inputField.classList.add('is-invalid');
        }
    }
    // Set the error message
    errorElement.textContent = message;
    errorElement.style.display = 'block';
}

function clearInlineErrors() {
    // Clear all inline error messages
    const errorElements = document.querySelectorAll('[id$="_error"]');
    errorElements.forEach(element => {
        element.style.display = 'none';
        element.textContent = '';
    });
    
    // Remove is-invalid class from all input fields
    const invalidInputs = document.querySelectorAll('.is-invalid');
    invalidInputs.forEach(input => {
        input.classList.remove('is-invalid');
    });
}

document.addEventListener('DOMContentLoaded', function() {
    // Fix for stuck modals or overlay bugs
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('hidden.bs.modal', function () {
            console.log('Modal hidden, removing modal-open class and backdrop');
            document.body.classList.remove('modal-open');
            document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
                console.log('Removing backdrop:', backdrop);
                backdrop.remove();
            });
        });
        
        modal.addEventListener('shown.bs.modal', function () {
            console.log('Modal shown');
        });
    });
    
    fetchGroups();
    fetchStudents();

    const calcSpinner = document.getElementById('calcSpinner');
    const groupSelect = document.getElementById('groupSelect');
    const groupDropdown = document.getElementById('groupDropdown');
    const dropdownSearch = document.getElementById('dropdownSearch');
    const groupOptions = document.getElementById('groupOptions');

    // Toggle dropdown visibility when clicking on the input
    groupSelect.addEventListener('click', function() {
        groupDropdown.classList.toggle('show');
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (!groupSelect.contains(e.target) && !groupDropdown.contains(e.target)) {
            groupDropdown.classList.remove('show');
        }
    });

    // Filter options based on search input
    dropdownSearch.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        const options = groupOptions.querySelectorAll('.dropdown-option');
        options.forEach(option => {
            const text = option.textContent.toLowerCase();
            if (text.includes(searchTerm)) {
                option.style.display = 'block';
            } else {
                option.style.display = 'none';
            }
        });
    });

    // Handle Enter key in groupSelect to show dropdown
    groupSelect.addEventListener('keydown', function(event) {
        if (event.key === 'Enter') {
            event.preventDefault();
            groupDropdown.classList.toggle('show');
        }
    });

    // Handle Enter key in dropdownSearch to select highlighted option
    dropdownSearch.addEventListener('keydown', function(event) {
        if (event.key === 'Enter') {
            event.preventDefault();
            // Find the first visible option
            const visibleOption = groupOptions.querySelector('.dropdown-option[style*="block"]');
            if (visibleOption) {
                // Simulate click on the option
                visibleOption.click();
            }
        }
    });

    document.getElementById('searchInput').addEventListener('input', filterTable);
    document.getElementById('zoneFilter').addEventListener('change', filterTable);
    document.querySelectorAll('.zone-filter').forEach(el => {
        el.addEventListener('click', function() {
            document.getElementById('zoneFilter').value = this.dataset.zone;
            filterTable();
            // animateZoneButton(this); // This function doesn't exist, so commenting out
        });
    });

    document.getElementById('createGroupBtn').addEventListener('click', function(e) {
        e.preventDefault();
        const groupName = document.getElementById('newGroupName').value.trim();
        if (!groupName) {
            alert('Please enter a group name');
            return;
        }
        fetch('/api/groups', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: `group_name=${encodeURIComponent(groupName)}`
        }).then(res => res.json()).then(data => {
            if (data.success) {
                alert('Group created successfully');
                document.getElementById('newGroupName').value = '';
                fetchGroups();
            } else {
                alert('Error creating group: ' + data.error);
            }
        }).catch(err => alert('Error creating group: ' + err.message));
    });

    // Handle group selection from dropdown
    groupOptions.addEventListener('click', function(e) {
        if (e.target.classList.contains('dropdown-option')) {
            const selectedGroup = e.target.textContent;
            groupSelect.value = selectedGroup;
            groupDropdown.classList.remove('show');
            sessionStorage.setItem('currentGroup', selectedGroup);
            fetchStudents(selectedGroup);
        }
    });

    document.getElementById('deleteGroupBtn').addEventListener('click', function() {
        const selectedGroup = document.getElementById('groupSelect').value;
        if (!selectedGroup) {
            alert('Please select a group to delete');
            return;
        }
        if (confirm(`Are you sure you want to delete the group "${selectedGroup}" and all its data? This action cannot be undone.`)) {
            fetch(`/api/groups/${encodeURIComponent(selectedGroup)}`, {
                method: 'DELETE'
            }).then(res => res.json()).then(data => {
                if (data.success) {
                    alert('Group deleted successfully');
                    fetchGroups();
                    fetchStudents();
                } else {
                    alert('Error deleting group: ' + data.error);
                }
            }).catch(err => alert('Error deleting group: ' + err.message));
        }
    });

    document.getElementById('studentForm').addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        const currentGroup = document.getElementById('groupSelect').value;
        if (!currentGroup) {
            alert('Please select a group before adding students');
            return;
        }
        fetch(`/api/students?group=${encodeURIComponent(currentGroup)}`, {
            method: 'POST',
            body: formData
        })
        .then(res => {
            if (!res.ok) {
                return res.json().then(errData => {
                    throw new Error(errData.errors ? errData.errors.join(', ') : 'Unknown error');
                });
            }
            return res.json();
        })
        .then(data => {
            if (data.success) {
                fetchStudents(currentGroup);
                this.reset();
                // Clear any previous error messages
                clearInlineErrors();
            } else {
                alert('Error adding student: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(err => {
            // Handle validation errors
            if (err.message.includes('value must be less than or equal to')) {
                // Parse the error message to extract field names and error messages
                const errorMessages = err.message.split(', ');
                errorMessages.forEach(errorMessage => {
                    if (errorMessage.includes('Previous Sem GPA')) {
                        showInlineError('previous_sem_percent', errorMessage);
                    } else if (errorMessage.includes('Extra Activities')) {
                        showInlineError('extra_activities_score', errorMessage);
                    } else if (errorMessage.includes('Projects')) {
                        showInlineError('project_count', errorMessage);
                    } else if (errorMessage.includes('Backlogs')) {
                        showInlineError('backlogs', errorMessage);
                    }
                });
            } else {
                alert('Error adding student: ' + err.message);
            }
        });
    });

    // Handle the save update button click for Bootstrap modal
    document.getElementById('saveUpdateBtn').addEventListener('click', function() {
        const id = document.getElementById('updateStudentId').value;
        const formData = new FormData(document.getElementById('updateStudentForm'));
        
        fetch(`/api/students/${id}?group=${encodeURIComponent(currentGroup)}`, {
            method: 'PUT',
            body: formData
        })
        .then(res => {
            if (!res.ok) {
                return res.json().then(errData => {
                    throw new Error(errData.errors ? errData.errors.join(', ') : 'Unknown error');
                });
            }
            return res.json();
        })
        .then(data => {
            if (data.success) {
                // Hide the modal
                const updateModal = bootstrap.Modal.getInstance(document.getElementById('updateStudentModal'));
                updateModal.hide();
                
                // Refresh the student list
                fetchStudents();
                
                // Show success message
                alert('Student updated successfully!');
            } else {
                alert('Error updating student: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(err => {
            // Handle validation errors for update modal
            if (err.message.includes('value must be less than or equal to')) {
                // Parse the error message to extract field names and error messages
                const errorMessages = err.message.split(', ');
                errorMessages.forEach(errorMessage => {
                    if (errorMessage.includes('Previous Sem GPA')) {
                        showInlineError('updatePreviousSemPercent', errorMessage);
                    } else if (errorMessage.includes('Extra Activities')) {
                        showInlineError('updateExtraActivitiesScore', errorMessage);
                    } else if (errorMessage.includes('Projects')) {
                        showInlineError('updateProjectCount', errorMessage);
                    } else if (errorMessage.includes('Backlogs')) {
                        showInlineError('updateBacklogs', errorMessage);
                    }
                });
            } else {
                alert('Error updating student: ' + err.message);
            }
        });
    });

    // Handle Enter key press in Bootstrap modal input fields
    document.getElementById('updateStudentForm').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            // Prevent default form submission
            e.preventDefault();
            
            // Trigger the save update button click
            document.getElementById('saveUpdateBtn').click();
        }
    });

    // Handle the save update button click for custom modal
    document.getElementById('customSaveUpdateBtn').addEventListener('click', function() {
        const id = document.getElementById('customUpdateStudentId').value;
        const formData = new FormData(document.getElementById('customUpdateStudentForm'));
        
        fetch(`/api/students/${id}?group=${encodeURIComponent(currentGroup)}`, {
            method: 'PUT',
            body: formData
        })
        .then(res => {
            if (!res.ok) {
                return res.json().then(errData => {
                    throw new Error(errData.errors ? errData.errors.join(', ') : 'Unknown error');
                });
            }
            return res.json();
        })
        .then(data => {
            if (data.success) {
                // Hide the custom modal
                document.getElementById('customUpdateStudentModal').classList.remove('show');
                
                // Refresh the student list
                fetchStudents();
                
                // Show success message
                alert('Student updated successfully!');
            } else {
                alert('Error updating student: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(err => {
            // Handle validation errors for custom update modal
            if (err.message.includes('value must be less than or equal to')) {
                // Parse the error message to extract field names and error messages
                const errorMessages = err.message.split(', ');
                errorMessages.forEach(errorMessage => {
                    if (errorMessage.includes('Previous Sem GPA')) {
                        showInlineError('customUpdatePreviousSemPercent', errorMessage);
                    } else if (errorMessage.includes('Extra Activities')) {
                        showInlineError('customUpdateExtraActivitiesScore', errorMessage);
                    } else if (errorMessage.includes('Projects')) {
                        showInlineError('customUpdateProjectCount', errorMessage);
                    } else if (errorMessage.includes('Backlogs')) {
                        showInlineError('customUpdateBacklogs', errorMessage);
                    }
                });
            } else {
                alert('Error updating student: ' + err.message);
            }
        });
    });

    // Handle Enter key press in custom modal input fields
    document.getElementById('customUpdateStudentForm').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            // Prevent default form submission
            e.preventDefault();
            
            // Trigger the save update button click
            document.getElementById('customSaveUpdateBtn').click();
        }
    });

    // Handle the close button click for custom modal
    document.getElementById('customModalClose').addEventListener('click', function() {
        document.getElementById('customUpdateStudentModal').classList.remove('show');
    });

    // Handle the cancel button click for custom modal
    document.getElementById('customModalCancel').addEventListener('click', function() {
        document.getElementById('customUpdateStudentModal').classList.remove('show');
    });

    // Load last selected group from sessionStorage
    const lastGroup = sessionStorage.getItem('currentGroup');
    if (lastGroup) {
        groupSelect.value = lastGroup;
        fetchStudents(lastGroup);
    }

    // Existing form Enter key submit handler
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                const target = event.target;
                if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {
                    event.preventDefault();
                    form.requestSubmit();
                }
            }
        });
    });
});

let studentsData = [];
let currentGroup = null;

function fetchGroups() {
    fetch('/api/groups').then(res => res.json()).then(data => {
        const groupOptions = document.getElementById('groupOptions');
        groupOptions.innerHTML = '';
        data.groups.forEach(group => {
            const option = document.createElement('div');
            option.className = 'dropdown-option';
            option.textContent = group;
            groupOptions.appendChild(option);
        });
        // Set current group if stored
        const storedGroup = sessionStorage.getItem('currentGroup');
        if (storedGroup && data.groups.includes(storedGroup)) {
            document.getElementById('groupSelect').value = storedGroup;
            currentGroup = storedGroup;
        }
    });
}

function fetchStudents(group) {
    if (group) {
        currentGroup = group;
    }
    if (!currentGroup) {
        // Remove alert completely as per user request
        return;
    }
    fetch(`/api/students?group=${encodeURIComponent(currentGroup)}`).then(res => res.json()).then(data => {
        studentsData = data.students;
        renderTable();
        updateZoneCounts();
    });
}

function renderTable() {
    const tbody = document.getElementById('studentsBody');
    tbody.innerHTML = '';
    let filtered = getFilteredStudents();
    filtered.forEach(s => {
        // Create red dot indicators for red zone fields
        const redFields = s.red_zone_fields || [];
        const weekendExamHtml = redFields.includes('weekend_exam') ? `${s.weekend_exam}<span class="red-dot"></span>` : s.weekend_exam;
        const midMarksHtml = redFields.includes('mid_marks') ? `${s.mid_marks}<span class="red-dot"></span>` : s.mid_marks;
        const crtScoreHtml = redFields.includes('crt_score') ? `${s.crt_score}<span class="red-dot"></span>` : s.crt_score;
        const attendanceHtml = redFields.includes('attendance_percent') ? `${s.attendance_percent}<span class="red-dot"></span>` : s.attendance_percent;
        const gdAttendanceHtml = redFields.includes('gd_attendance') ? `${s.gd_attendance}<span class="red-dot"></span>` : s.gd_attendance;
        const prevSemHtml = redFields.includes('previous_sem_percent') ? `${s.previous_sem_percent}<span class="red-dot"></span>` : s.previous_sem_percent;
        const extraActivitiesHtml = redFields.includes('extra_activities_score') ? `${s.extra_activities_score}<span class="red-dot"></span>` : s.extra_activities_score;
        const projectCountHtml = redFields.includes('project_count') ? `${s.project_count}<span class="red-dot"></span>` : s.project_count;
        const backlogsHtml = redFields.includes('backlogs') ? `${s.backlogs}<span class="red-dot"></span>` : s.backlogs;

        let tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${s.name}</td>
            <td>${weekendExamHtml}</td>
            <td>${midMarksHtml}</td>
            <td>${crtScoreHtml}</td>
            <td>${attendanceHtml}</td>
            <td>${gdAttendanceHtml}</td>
            <td>${prevSemHtml}</td>
            <td>${extraActivitiesHtml}</td>
            <td>${projectCountHtml}</td>
            <td>${backlogsHtml}</td>
            <td><span class="badge bg-${zoneColor(s.zone)}">${s.zone}</span></td>
            <td>
                <button class="btn btn-sm btn-outline-primary me-1" onclick="updateStudent('${s.id}')">Update</button>
                <button class="btn btn-sm btn-outline-danger" onclick="removeStudent('${s.id}')">Remove</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function getFilteredStudents() {
    const search = document.getElementById('searchInput').value.toLowerCase();
    const zone = document.getElementById('zoneFilter').value;
    return studentsData.filter(s => {
        let match = s.name.toLowerCase().includes(search);
        if (zone && s.zone !== zone) match = false;
        return match;
    });
}

function filterTable() {
    renderTable();
    updateZoneCounts();
}

function updateZoneCounts() {
    let good = studentsData.filter(s => s.zone === 'Good').length;
    let avg = studentsData.filter(s => s.zone === 'Average').length;
    let red = studentsData.filter(s => s.zone === 'Red Zone').length;
    document.getElementById('safeCount').textContent = good;
    document.getElementById('avgCount').textContent = avg;
    document.getElementById('redCount').textContent = red;
}

function zoneColor(zone) {
    if (zone === 'Good') return 'success';
    if (zone === 'Average') return 'warning';
    if (zone === 'Red Zone') return 'danger';
    return 'secondary';
}

window.removeStudent = function(id) {
    if (!confirm('Are you sure you want to remove this student?')) return;
    fetch(`/api/students/${id}?group=${encodeURIComponent(currentGroup)}`, { method: 'DELETE' })
        .then(res => res.json())
        .then(data => fetchStudents());
}

window.updateStudent = function(id) {
    console.log('updateStudent called with id:', id);
    // Find the student data from the studentsData array
    const studentData = studentsData.find(s => s.id === id);
    
    if (!studentData) {
        console.error('Student data not found for id:', id);
        alert('Student data not found');
        return;
    }
    
    console.log('Found student data:', studentData);
    
    // Populate the custom modal with student data
    document.getElementById('customUpdateStudentId').value = id;
    document.getElementById('customUpdateName').value = studentData.name || '';
    document.getElementById('customUpdateWeekendExam').value = studentData.weekend_exam || '';
    document.getElementById('customUpdateMidMarks').value = studentData.mid_marks || '';
    document.getElementById('customUpdateCrtScore').value = studentData.crt_score || '';
    document.getElementById('customUpdateAttendancePercent').value = studentData.attendance_percent || '';
    document.getElementById('customUpdateGdAttendance').value = studentData.gd_attendance || '';
    document.getElementById('customUpdatePreviousSemPercent').value = studentData.previous_sem_percent || '';
    document.getElementById('customUpdateBacklogs').value = studentData.backlogs || '';
    document.getElementById('customUpdateExtraActivitiesScore').value = studentData.extra_activities_score || '';
    document.getElementById('customUpdateProjectCount').value = studentData.project_count || '';
    
    console.log('Custom modal populated with student data');
    
    // Show the custom modal
    document.getElementById('customUpdateStudentModal').classList.add('show');
    console.log('Custom modal shown');
}
