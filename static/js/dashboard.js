function loadBudgetData(budgetData) {
  budgets = JSON.parse(budgetData);
  loadBudgetCharts(budgets);
}

$("#quickExpenseModal").on("shown.bs.modal", function () {
  $("#description").trigger("focus");
});

function loadBudgetCharts(budgets) {
  if (budgets == null) {
    return;
  }
  // Loop through the budgets and build the charts
  else {
    let chartElement = [];
    let budgetCharts = [];
    for (i = 0; i < budgets.length; i++) {
      chartElement[i] = document
        .getElementById("budgetChart." + i)
        .getContext("2d");
      budgetCharts[i] = new Chart(chartElement[i], {
        type: "doughnut",
        data: {
          labels: ["Spent", "Remaining"],
          datasets: [
            {
              label: budgets[i].name,
              data: [
                Math.round(budgets[i].spent * 100) / 100,
                Math.round(budgets[i].remaining * 100) / 100,
              ],
              backgroundColor: [
                "rgba(240, 173, 78, 1)",
                "rgba(2, 184, 117, 1)",
              ],
              borderColor: ["rgba(192, 138, 62, 1)", "rgba(1, 147, 93, 1)"],
              borderWidth: 2,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          legend: {
            labels: {
              fontColor: "black",
            },
          },
        },
      });
    }
  }
}
