(async () => {
  const currentGroup = sessionStorage.getItem('currentGroup');
  if (!currentGroup) {
    console.log('No group selected.');
    return;
  }
  try {
    const response = await fetch(`/api/students?group=${encodeURIComponent(currentGroup)}`);
    const data = await response.json();
    if (!data.students) {
      console.log('No student data found.');
      return;
    }
    const counts = { Good: 0, Average: 0, 'Red Zone': 0 };
    data.students.forEach(student => {
      if (counts.hasOwnProperty(student.zone)) {
        counts[student.zone]++;
      }
    });
    console.log(`Categorization data for group "${currentGroup}":`);
    console.log(counts);
  } catch (error) {
    console.error('Error fetching categorization data:', error);
  }
})();
