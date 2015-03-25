'use strict'
/**
 * Declare our main AngularJS application module with its dependencies
 */
var opinionate = angular.module('opinionate', ['ngRoute', 'ngTouch']);

/**
 * Configure our application's routes. This is similar to configuring webapp2
 * handlers in a Python AppEngine module but these will strictly be interpreted
 * client-side in the browser.
 */
opinionate.config(function($routeProvider) {
  $routeProvider.when('/', {
    'controller': 'TopicsController',
    'templateUrl': '/templates/topics.html'
  })
  when('/new', {
    'controller': 'NewTopicController',
    'templateUrl': '/templates/new_topic.html'
  })
  .when('/profile', {
    'controller': 'ProfileController',
    'templateUrl': '/templates/profile.html'
  })
  .otherwise('/');
});

/**
 * Directives are ways of packaging HTML and associated logic together
 * into reusable components. Think of them as advanced tags with accompanying
 * business rules.
 */
opinionate.directive('loadingIndicator', function() {
  return {
    'restrict': 'E',
    'replace': true,
    'templateUrl': '/templates/loading_indicator.html',
    /* Directives have their own $scope. Using the '=' value creates a two-way
     * binding between the variable in the directive's scope and the variable
     * from the parent scope it was declared in.
     */
    'scope': {
      'loading': '=',
      'label': '='
    }
  };
});

/**
 * Alert directive provides a simple way of declaring an alert status message.
 */
opinionate.directive('alert', function() {
  return {
    'restrict': 'E',
    'replace': true,
    'templateUrl': '/templates/alert.html',
    'scope': {
      'alertType': '@',
      'message': '@',
      'close': '&'
    }
  };
});

/**
 * NavbarController will be used to set active classes on nav list elements
 * based on the active route.
 */
opinionate.controller('NavbarController', function($scope, $location) {
  // Function local variable to represent active route
  var activeRoute_ = '';

  /**
   * isRouteActive is a $scope level function which means that it can be
   * invoked from the HTML element to which this controller is bound. This
   * will return true if the path provided matches the activeRoute.
   */
  $scope.isRouteActive = function(path) {
    return activeRoute_ === path;
  };

  /**
   * This is an event listener for route changes. We'll intercept the new
   * URL and use it to set activeRoute_.
   */
  $scope.$on('$locationChangeStart', function() {
    activeRoute_ = $location.path();
  });
});

/**
 * The ProfileController will be used to manage the fetching/storing of a
 * user's profile information.
 */
opinionate.controller('ProfileController', function($scope, $http) {

  /**
   * Scope-level profile data
   */
  $scope.profile = {};

  /**
   * List of objects for reflecting application alerts.
   */
  $scope.alerts = [];

  /**
   * Close an alert by removing it from the alerts array
   */
  $scope.closeAlert = function(index) {
    $scope.alerts.splice(index, 1);
  };

  /**
   * Fetch profile information when instantiated.
   */
  $scope.loading = true;
  $scope.loadingLabel = 'Retrieving profile...';
  $http.get('/profile')
    .success(function(profile) {
      $scope.profile = profile;
    })
    .error(function(data, status) {
      $scope.alerts.push({
        'alertType': 'danger', 'message': 'Unable to load profile data.'
      });
    })
    .finally(function() {
      $scope.loading = false;
      $scope.loadingLabel = '';
    });

  /**
   * Function to handle upload a profile avatar
   */
  $scope.uploadAvatar = function(fileList) {
    var imageTypes = ['image/gif', 'image/jpeg', 'image/pjpeg', 'image/png'];
    if (fileList.length === 1) {
      var picture = fileList[0];
      if (imageTypes.indexOf(picture.type) > -1) {
        var formData = new FormData();
        //Take the first selected file
        formData.append('avatar', picture);
        $scope.loading = true;
        $scope.loadingLabel = 'Uploading avatar...';
        $http.post('/profile', formData, {
            headers: {'Content-Type': undefined},
            transformRequest: angular.identity
        })
          .success(function(profile) {
            profile.avatar += '?ts=' + Date.now();
            $scope.profile = profile;
            $scope.alerts.push({
              'alertType': 'success', 'message': 'Avatar uploaded.'
            });
          })
          .error(function() {
            $scope.alerts.push({
              'alertType': 'danger', 'message': 'Unable to upload avatar'
            });
          })
          .finally(function() {
            $scope.loading = false;
            $scope.loadingLabel = '';
          });
      }
      else {
        $scope.$apply(function() {
          $scope.alerts.push({
            'alertType': 'danger', 'message': 'You must provide an image file.'
          });
        });
      }
    }
  };
});

/**
 * The NewTopicController will be used to create new topics to vote on
 */
opinionate.controller('NewTopicController', function($scope, $http) {

  /**
   * Scope-level topic data for use as form model
   */
  $scope.topic = {
      'name': '',
      'tags': '',
      'image': null
  };

  /**
   * List of objects for reflecting application alerts.
   */
  $scope.alerts = [];

  /**
   * Close an alert by removing it from the alerts array
   */
  $scope.closeAlert = function(index) {
    $scope.alerts.splice(index, 1);
  };

  /**
   * Function to handle post a new topic
   */
  $scope.submit = function() {
    $scope.loading = true;
    $scope.loadingLabel = 'Creating new topic...';
    // Build form data
    var formData = new FormData();
    for (var f in $scope.topic) {
      if ($scope.topic[f]) {
        formData.append(f, $scope.topic[f]);
      }
    }

    $http.post('/topics', formData, {
        headers: {'Content-Type': undefined},
        transformRequest: angular.identity
    })
      .success(function(profile) {
        $scope.alerts.push({
          'alertType': 'success', 'message': 'New topic created'
        });
        $scope.topic = {
            'name': '',
            'tags': '',
            'image': null
        };
      })
      .error(function() {
        $scope.alerts.push({
          'alertType': 'danger', 'message': 'Unable to create topic'
        });
      })
      .finally(function() {
        $scope.loading = false;
        $scope.loadingLabel = '';
      });
  };

  /**
   * Function to handle setting a topic image
   */
  $scope.uploadImage = function(fileList) {
    $scope.$apply(function() {
      var imageTypes = ['image/gif', 'image/jpeg', 'image/pjpeg', 'image/png'];
      if (fileList.length === 1) {
        var picture = fileList[0];
        if (imageTypes.indexOf(picture.type) > -1) {
          $scope.topic.image = picture;
        }
        else {
          $scope.alerts.push({
            'alertType': 'danger', 'message': 'You must provide an image file.'
          });
        }
      }
    });
  }; // end uploadImage
});

/**
 * The NewTopicController will be used to create new topics to vote on
 */
opinionate.controller('TopicsController', function($scope, $http) {

  /**
   * Scope-level topics data
   */
  $scope.topics = [];

  /**
   * Scope-level map of Topics the user created
   */
  $scope.myTopics = {};


  /**
   * Scope-level map of Votes from the user
   */
  $scope.myVotes = {};

  /**
   * Scope-level boolean for indicating whether voting is enabled
   */
  $scope.canVote = false;

  /**
   * List of objects for reflecting application alerts.
   */
  $scope.alerts = [];

  /**
   * Close an alert by removing it from the alerts array
   */
  $scope.closeAlert = function(index) {
    $scope.alerts.splice(index, 1);
  };

  /**
   * Fetch topics information when instantiated.
   */
  $scope.loading = true;
  $scope.loadingLabel = 'Retrieving latest topics...';
  $http.get('/topics')
    .success(function(data) {
      $scope.topics = data.topics;
      $scope.canVote = data.can_vote;
      $scope.myTopics = data.my_topics;
      $scope.myVotes = data.my_votes;
    })
    .error(function(data, status) {
      $scope.alerts.push({
        'alertType': 'danger', 'message': 'Unable to load topics data.'
      });
    })
    .finally(function() {
      $scope.loading = false;
      $scope.loadingLabel = '';
    });

  /**
   * Returns true if the user is not logged in, created this topics, or
   * has already voted on this topic
   */
  $scope.ineligibleForVote = function(topicId) {
    return !$scope.canVote ||
      (topicId in $scope.myTopics) ||
      (topicId in $scope.myVotes);
  };

  /**
   * Handle voting for a topic.
   */
  $scope.vote = function(index, vote) {
    var topic = $scope.topics[index];
    if (topic) {
      var url = '/topics/' + topic.id + '/' + vote;
      $http.put(url)
        .success(function(data) {
          $scope.topics[index] = data.topic;
          $scope.myVotes = data.my_votes;
        })
        .error(function(data, status) {
          $scope.alerts.push({
            'alertType': 'danger',
            'message': 'Unable to record vote for ' + topic.id
          });
        })
    }
  };

});
