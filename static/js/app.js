// Lean Prover Annotator - Index Page

document.addEventListener('DOMContentLoaded', function() {
    // Add Problem Form
    document.getElementById('showAddFormBtn').addEventListener('click', function() {
        document.getElementById('addProblemForm').style.display = 'block';
        document.getElementById('importForm').style.display = 'none';
    });
    
    document.getElementById('saveProblemBtn').addEventListener('click', saveProblem);
    document.getElementById('cancelEditBtn').addEventListener('click', cancelEdit);
    
    // CSV Import
    document.getElementById('showImportBtn').addEventListener('click', function() {
        document.getElementById('importForm').style.display = 'block';
        document.getElementById('addProblemForm').style.display = 'none';
    });
    
    document.getElementById('importCsvBtn').addEventListener('click', importCsv);
    document.getElementById('cancelImportBtn').addEventListener('click', function() {
        document.getElementById('importForm').style.display = 'none';
        document.getElementById('importResult').style.display = 'none';
    });

    // Search and Filter
    var searchInput = document.getElementById('searchInput');
    var difficultyFilter = document.getElementById('difficultyFilter');

    if (searchInput) {
        searchInput.addEventListener('input', filterProblems);
    }
    if (difficultyFilter) {
        difficultyFilter.addEventListener('change', filterProblems);
    }
});

function filterProblems() {
    var searchQuery = document.getElementById('searchInput').value.toLowerCase();
    var difficulty = document.getElementById('difficultyFilter').value;
    var cards = document.querySelectorAll('.problem-card');

    cards.forEach(function(card) {
        var title = card.querySelector('h3').textContent.toLowerCase();
        var desc = card.querySelector('.problem-desc').textContent.toLowerCase();
        var cardDifficulty = card.getAttribute('data-difficulty') || 'medium';

        var matchesSearch = title.includes(searchQuery) || desc.includes(searchQuery);
        var matchesDifficulty = difficulty === 'all' || cardDifficulty === difficulty;

        if (matchesSearch && matchesDifficulty) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });

    // Show "no results" message if needed
    var visibleCards = document.querySelectorAll('.problem-card:not([style*="display: none"])');
    var grid = document.getElementById('problemsGrid');
    var noResults = document.getElementById('noResults');

    if (visibleCards.length === 0) {
        if (!noResults) {
            noResults = document.createElement('div');
            noResults.id = 'noResults';
            noResults.className = 'no-results';
            noResults.innerHTML = '<p>No problems found matching your criteria.</p>';
            grid.appendChild(noResults);
        }
        noResults.style.display = '';
    } else if (noResults) {
        noResults.style.display = 'none';
    }
}

function openProblem(id) {
    window.location.href = '/problem/' + id;
}

function editProblem(id) {
    fetch('/api/problem/' + id)
        .then(function(res) { return res.json(); })
        .then(function(problem) {
            document.getElementById('editProblemId').value = id;
            document.getElementById('problemTitle').value = problem.title;
            document.getElementById('problemDescription').value = problem.description;
            document.getElementById('problemNatural').value = problem.natural_language || '';
            document.getElementById('problemDifficulty').value = problem.difficulty;
            
            document.getElementById('formTitle').textContent = 'Edit Problem';
            document.getElementById('saveProblemBtn').textContent = 'Update Problem';
            document.getElementById('addProblemForm').style.display = 'block';
            document.getElementById('importForm').style.display = 'none';
        });
}

function deleteProblem(id) {
    if (!confirm('Are you sure you want to delete this problem?')) return;
    
    fetch('/api/problem/' + id, { method: 'DELETE' })
        .then(function() {
            location.reload();
        })
        .catch(function(err) {
            alert('Error deleting problem: ' + err.message);
        });
}

function saveProblem() {
    var id = document.getElementById('editProblemId').value;
    var title = document.getElementById('problemTitle').value.trim();
    var description = document.getElementById('problemDescription').value.trim();
    var natural = document.getElementById('problemNatural').value.trim();
    var difficulty = document.getElementById('problemDifficulty').value;
    
    if (!title || !description) {
        alert('Title and description are required');
        return;
    }
    
    var data = {
        title: title,
        description: description,
        natural_language: natural,
        difficulty: difficulty
    };
    
    var url = '/api/problems';
    var method = 'POST';
    
    if (id) {
        url = '/api/problem/' + id;
        method = 'PUT';
    }
    
    fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(function(res) { return res.json(); })
    .then(function() {
        location.reload();
    })
    .catch(function(err) {
        alert('Error saving problem: ' + err.message);
    });
}

function cancelEdit() {
    document.getElementById('editProblemId').value = '';
    document.getElementById('problemTitle').value = '';
    document.getElementById('problemDescription').value = '';
    document.getElementById('problemNatural').value = '';
    document.getElementById('problemDifficulty').value = 'medium';
    
    document.getElementById('formTitle').textContent = 'Add New Problem';
    document.getElementById('saveProblemBtn').textContent = 'Add Problem';
    document.getElementById('addProblemForm').style.display = 'none';
}

function importCsv() {
    var fileInput = document.getElementById('csvFile');
    var file = fileInput.files[0];
    
    if (!file) {
        alert('Please select a CSV file');
        return;
    }
    
    var formData = new FormData();
    formData.append('file', file);
    
    var resultDiv = document.getElementById('importResult');
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = '<p>Importing...</p>';
    
    fetch('/api/problems/import-csv', {
        method: 'POST',
        body: formData
    })
    .then(function(res) { return res.json(); })
    .then(function(result) {
        if (result.success) {
            var html = '<p class="success">Successfully imported ' + result.imported + ' problems!</p>';
            if (result.errors && result.errors.length > 0) {
                html += '<p class="warning">Warnings:</p><ul>';
                result.errors.forEach(function(e) {
                    html += '<li>' + e + '</li>';
                });
                html += '</ul>';
            }
            resultDiv.innerHTML = html;
            
            // Reload page after short delay
            setTimeout(function() {
                location.reload();
            }, 2000);
        } else {
            resultDiv.innerHTML = '<p class="error">Error: ' + (result.error || 'Unknown error') + '</p>';
        }
    })
    .catch(function(err) {
        resultDiv.innerHTML = '<p class="error">Error: ' + err.message + '</p>';
    });
}